has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
from qgis.utils import iface

def copy_layer(layer):
    layer.selectAll()
    clone_layer = processing.run("native:saveselectedfeatures", {'INPUT': layer, 'OUTPUT': 'memory:'})['OUTPUT']
    layer.removeSelection()
    QgsProject.instance().addMapLayer(clone_layer)
    return clone_layer

def uniquely_name(theLayer, name_field='Name'):
    features = theLayer.getFeatures()
    print(theLayer)
    field_index = theLayer.fields().indexOf(name_field)
    theLayer.startEditing()
    # Keep a set of names previously used
    previous_names = set()
    for feature in features:
        name = feature[name_field]
        # print(f'{feature.id()}:{name}')
        # if not in set add it and move to the next
        if name not in previous_names:
            previous_names.add(name)
        else:
            # find a unique name (add .#) until we are unique
            num_append = 2
            unique_name = f'{name}.{num_append}'
            while (unique_name in previous_names):
                num_append = num_append + 1
                unique_name = f'{name}.{num_append}'
            # we found a unique name
            print(f'renaming {name} to {unique_name}')
            previous_names.add(unique_name)
            theLayer.changeAttributeValue(feature.id(), field_index, unique_name)
    print('Commiting changes')
    theLayer.commitChanges()

layer = iface.activeLayer()
layer_copy = copy_layer(layer)
uniquely_name(layer_copy)