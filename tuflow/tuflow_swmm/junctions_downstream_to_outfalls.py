has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from qgis.core import (QgsFeature,
                       QgsField,
                       QgsPoint,
                       QgsVectorLayerJoinInfo,
                       )
from PyQt5.QtCore import QVariant


def create_junction_features(row, new_layer, features_to_add):
    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsPoint(row['geometry'].coords[0][0],
                        row['geometry'].coords[0][1])

    # validate_errors = new_geom.validateGeometry()
    # if validate_errors:
    #    print(f'Errors found converting {row["Name"]}: {validate_errors}')
    new_feat.setGeometry(new_geom)

    new_feat.setAttribute('Name', row['Name'])
    new_feat.setAttribute('Elev', row['Elev'])
    new_feat.setAttribute('Ymax', row['Ymax'])
    new_feat.setAttribute('Y0', row['Y0'])
    new_feat.setAttribute('Ysur', row['Ysur'])
    new_feat.setAttribute('Apond', row['Apond'])

    features_to_add.append(new_feat)

    return None


def create_outfall_features(row, new_layer, features_to_add):
    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsPoint(row['geometry'].coords[0][0],
                        row['geometry'].coords[0][1])

    # validate_errors = new_geom.validateGeometry()
    # if validate_errors:
    #    print(f'Errors found converting {row["Name"]}: {validate_errors}')
    new_feat.setGeometry(new_geom)

    new_feat.setAttribute('Name', row['Name'])
    new_feat.setAttribute('Elev', row['Elev'])
    new_feat.setAttribute('Type', row['Type'])
    new_feat.setAttribute('Stage', row['Stage'])
    new_feat.setAttribute('Tcurve', row['Tcurve'])
    new_feat.setAttribute('Tseries', row['Tseries'])
    new_feat.setAttribute('Gated', row['Gated'])
    new_feat.setAttribute('RouteTo', row['RouteTo'])

    features_to_add.append(new_feat)

    return None


def downstream_junctions_to_outfalls(
        gdf_input_junctions,
        gdf_input_conduits,
        feedback=ScreenProcessingFeedback()):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    # If we don't have any junctions or conduits stop
    if len(gdf_input_junctions) == 0:
        feedback.reportError('Junctions layer is empty. Aborting.', True)
        return

    if len(gdf_input_conduits) == 0:
        feedback.reportError('Conduits layer is empty. Aborting.', True)
        return

    feedback.pushInfo(f'Number of input junctions: {len(gdf_input_junctions)}')
    feedback.pushInfo(f'Number of input conduits: {len(gdf_input_conduits)}')

    gdf_conduits2 = gdf_input_conduits.merge(gdf_input_conduits[['From Node']],
                                             how='left',
                                             left_on='To Node',
                                             right_on='From Node',
                                             suffixes=(None, '_down'))
    gdf_conduits2['HasDownstream'] = ~gdf_conduits2['From Node_down'].isnull()

    gdf_conduits3 = gdf_conduits2.merge(
        gdf_conduits2[['To Node']],
        how='left',
        left_on='From Node',
        right_on='To Node',
        suffixes=(None, '_up'))
    gdf_conduits3['HasUpstream'] = ~gdf_conduits3['To Node_up'].isnull()

    gdf_conduits_no_upstream = gdf_conduits3[~gdf_conduits3['HasUpstream']].drop_duplicates(subset='From Node')
    gdf_conduits_no_downstream = gdf_conduits3[~gdf_conduits3['HasDownstream']].drop_duplicates(subset='To Node')

    if len(gdf_conduits_no_downstream) == 0 and len(gdf_conduits_no_upstream) == 0:
        feedback.reportError(
            'No upstream and downstream channels identified. Double-check that the "From Node" and "To Node" fields have been filled in',
            True)

    # print(gdf_conduits3)

    # We want to identify the downstream nodes for channels that do not have a downstream
    nodes_to_convert = gdf_conduits3.loc[~gdf_conduits3['HasDownstream'], 'To Node'].unique()
    # print(nodes_to_convert)

    gdf_junctions_out = None
    gdf_outfalls_out = None

    gdf_junctions_out = gdf_input_junctions[~gdf_input_junctions['Name'].isin(nodes_to_convert)].copy(deep=True)
    # print(gdf_junctions_out)

    gdf_outfalls_out = gdf_input_junctions[gdf_input_junctions['Name'].isin(nodes_to_convert)].copy(deep=True)

    # Setup the correct attributes
    gdf_outfalls_out['Type'] = 'FIXED'
    gdf_outfalls_out['Stage'] = gdf_outfalls_out['Elev']
    gdf_outfalls_out['Tcurve'] = None
    gdf_outfalls_out['Tseries'] = None
    gdf_outfalls_out['Gated'] = None
    gdf_outfalls_out['RouteTo'] = None

    gdf_outfalls_out = gdf_outfalls_out[
        [
            'Name',
            'Elev',
            'Type',
            'Stage',
            'Tcurve',
            'Tseries',
            'Gated',
            'RouteTo',
            'geometry',
        ]
    ]

    feedback.pushInfo(f'Number of outfalls created: {len(gdf_outfalls_out)}')
    # print(gdf_outfalls_out)

    return gdf_junctions_out, gdf_outfalls_out


def downstream_junctions_to_outfalls_from_files(
        junctions_in_filename,
        junctions_in_layername,
        conduits_in_filename,
        conduits_in_layername,
        junctions_out_filename,
        junctions_out_layername,
        outfalls_out_filename,
        outfalls_out_layername,
        feedback=ScreenProcessingFeedback()):
    gdf_junctions_in = gpd.read_file(junctions_in_filename, layer=junctions_in_layername)
    gdf_conduits_in = gpd.read_file(conduits_in_filename, layer=conduits_in_layername)

    gdf_junctions_out, gdf_outfalls_out = downstream_junctions_to_outfalls(
        gdf_junctions_in,
        gdf_conduits_in,
        feedback
    )

    if gdf_junctions_out is not None:
        gdf_junctions_out.to_file(junctions_out_filename, layer=junctions_out_layername)

    if gdf_outfalls_out is not None:
        gdf_outfalls_out.to_file(outfalls_out_filename, layer=outfalls_out_layername)


def downstream_junctions_to_outfalls_from_qgis(
        input_junctions,
        input_conduits,
        output_junctions,
        output_outfalls,
        feedback=ScreenProcessingFeedback()):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    # lay_conduits_mem = QgsVectorLayer(f"LineString?crs={layer.crs}", 'bc_layer', 'memory')
    # dp = lay_conduits_mem.dataProvider()
    dp_junctions = output_junctions.dataProvider()
    output_junctions.startEditing()
    dp_junctions.addAttributes([
        QgsField("Name", QVariant.String),
        QgsField("Elev", QVariant.Double),
        QgsField("Ymax", QVariant.Double),
        QgsField("Y0", QVariant.Double),
        QgsField("Ysur", QVariant.Double),
        QgsField("Apond", QVariant.Double),
    ])
    output_junctions.updateFields()

    dp_outfalls = output_outfalls.dataProvider()
    output_outfalls.startEditing()
    dp_outfalls.addAttributes([
        QgsField("Name", QVariant.String),
        QgsField("Elev", QVariant.Double),
        QgsField("Type", QVariant.String),
        QgsField("Stage", QVariant.Double),
        QgsField("Tcurve", QVariant.String),
        QgsField("Tseries", QVariant.Double),
        QgsField("Gated", QVariant.String),
        QgsField("RouteTo", QVariant.String),
    ])
    output_outfalls.updateFields()

    gdf_junctions = gpd.GeoDataFrame.from_features(input_junctions.getFeatures())

    gdfs_conduits = []
    for conduit_layer in input_conduits:
        gdfs_conduits.append(gpd.GeoDataFrame.from_features(conduit_layer.getFeatures()))
    gdf_conduits = pd.concat(gdfs_conduits)

    rval = downstream_junctions_to_outfalls(
        gdf_junctions,
        gdf_conduits,
        feedback
    )
    if rval is None:
        return

    gdf_junctions_out, gdf_outfalls_out = rval

    feedback.pushInfo(', '.join([str(x) for x in gdf_junctions_out.columns]))

    junctions_to_add = []
    gdf_junctions_out.apply(lambda x: create_junction_features(x, output_junctions, junctions_to_add),
                            axis=1)
    dp_junctions.addFeatures(junctions_to_add)

    outfalls_to_add = []
    gdf_outfalls_out.apply(lambda x: create_outfall_features(x, output_outfalls, outfalls_to_add),
                           axis=1)
    dp_outfalls.addFeatures(outfalls_to_add)

    return
