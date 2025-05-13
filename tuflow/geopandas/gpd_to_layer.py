from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsFeature, QgsGeometry, QgsField, QgsFields

has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    from pandas.api.types import is_integer_dtype, is_numeric_dtype

    has_gpd = True
except ImportError:
    pass  # defaulted to false

from ..compatibility_routines import QT_DOUBLE, QT_STRING, QT_INT


def geopandas_dtype_to_field_type(dtype):
    if is_integer_dtype(dtype):
        return QT_INT
    elif is_numeric_dtype(dtype):
        return QT_DOUBLE
    elif str(type(dtype)) == 'geometry':
        return None
    else:
        return QT_STRING


def extract_gdf_fields(gdf):
    fields = []
    for col, col_type in gdf.dtypes.items():
        if col == 'geometry':
            continue
        qvar = geopandas_dtype_to_field_type(col_type)
        if qvar is not None:
            fields.append(QgsField(col, qvar))

    qfields_out = QgsFields()
    for field in fields:
        qfields_out.append(field)
    return qfields_out


def create_feature(row, new_layer, features_to_add):
    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsGeometry.fromWkt(row['geometry'].wkt)

    new_feat.setGeometry(new_geom)

    for q_field in new_layer.fields().toList():
        col = q_field.name()
        new_feat.setAttribute(col, row[col])

    features_to_add.append(new_feat)

    return None


def fill_layer_from_gdf(layer, gdf):
    dp = layer.dataProvider()
    layer.startEditing()
    dp.addAttributes(extract_gdf_fields(gdf))
    layer.updateFields()

    features_to_add = []
    gdf.apply(
        lambda x: create_feature(x, layer, features_to_add),
        axis=1,
    )
    dp.addFeatures(features_to_add)

    layer.commitChanges()
