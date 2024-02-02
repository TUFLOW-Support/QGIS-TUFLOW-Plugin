has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
from qgis.core import (QgsFeature,
                       QgsField,
                       QgsPoint,
                       QgsVectorLayerJoinInfo,
                       )
import pandas as pd

from PyQt5.QtCore import QVariant

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def remove_layer_joins(layer, feedback):
    joinsInfo = layer.vectorJoins()
    for joinInfo in joinsInfo:
        ok = layer.removeJoin(joinInfo.joinLayerId())
        if not ok:
            feedback.reportError('Unable to remove join. May interfere with tool')


def create_junction_features(row, new_layer, features_to_add):
    # print(row)
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


def get_junction_atts(features_junctions,
                      lays_subcatch,
                      lays_inlet_usage,
                      lays_bc_conn,
                      inlet_ysur,
                      inlet_apond,
                      hx_ysur,
                      hx_apond,
                      no_conn_ysur,
                      no_conn_apond,
                      initialize_ymax,
                      no_ponding_for_subcatch_nodes,
                      ymax_from_inlet_elev,
                      feedback=ScreenProcessingFeedback()):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    gdf_junct = gpd.GeoDataFrame.from_features(features_junctions)

    gdf_inlet_usage = None
    if lays_inlet_usage is not None and len(lays_inlet_usage) > 0:
        gdfs_inlet_usage = []
        for lay_inlet_usage in lays_inlet_usage:
            gdfs_inlet_usage.append(gpd.GeoDataFrame.from_features(lay_inlet_usage.getFeatures()))

        for gdf in gdfs_inlet_usage:
            feedback.pushInfo(f'Columns: {", ".join([str(c) for c in gdf.columns])}')
        gdf_inlet_usage = pd.concat(gdfs_inlet_usage, axis=0)
        gdf_inlet_usage = gdf_inlet_usage[['geometry', 'Inlet', 'Elevation']]

    gdfs_bc_conn = []
    for lay_bc_conn in lays_bc_conn:
        gdfs_bc_conn.append(gpd.GeoDataFrame.from_features(lay_bc_conn.getFeatures()))

    gdf_bc_conn = None
    if len(gdfs_bc_conn) > 0:
        gdf_bc_conn = pd.concat(gdfs_bc_conn, axis=0)
        gdf_bc_conn = gdf_bc_conn[['geometry', 'Type']].rename(columns={'Type': 'BC_Type'})

    # feedback.pushInfo(gdf_bc_conn.to_string(col_space=[30] * len(gdf_bc_conn.columns)))

    gdfs_subcatch = []
    for lay_subcatch in lays_subcatch:
        gdfs_subcatch.append(gpd.GeoDataFrame.from_features(lay_subcatch.getFeatures()))

    gdf_subcatch = None
    if len(gdfs_subcatch) > 0:
        gdf_subcatch = pd.concat(gdfs_subcatch, axis=0)
        gdf_subcatch = gdf_subcatch[['Name', 'Outlet']].rename(
            columns={
                'Name': 'Sub_Name',
                'Outlet': 'Sub_Outlet',
            }
        )

    if gdf_inlet_usage is not None:
        gdf_junct_inlets = gpd.sjoin(gdf_junct,
                                     gdf_inlet_usage,
                                     how='left',
                                     predicate='intersects',
                                     rsuffix='_in')
    else:
        gdf_junct_inlets = gdf_junct
        gdf_junct_inlets['Inlet'] = None

    if gdf_bc_conn is not None:
        gdf_all = gpd.sjoin_nearest(gdf_junct_inlets,
                                    gdf_bc_conn[['geometry', 'BC_Type']],
                                    how='left',
                                    max_distance=0.001,
                                    rsuffix='_bc_conn')
        gdf_all = gdf_all.drop_duplicates(subset='Name')
    else:
        gdf_all = gdf_junct_inlets
        gdf_all['geometry_bc_conn'] = None
        gdf_all['BC_Type'] = None

    if gdf_subcatch is not None:
        gdf_all = gdf_all.merge(gdf_subcatch,
                                how='left',
                                left_on='Name',
                                right_on='Sub_Outlet')
    else:
        gdf_all['Sub_Name'] = None

    # feedback.pushInfo(gdf_all.to_string(col_space=[30] * len(gdf_all.columns)))

    gdf_all['is_outlet'] = ((gdf_all['Sub_Name'] is not None) &
                            (gdf_all['Sub_Name'].astype(str) != 'None') &
                            (gdf_all['Sub_Name'].astype(str) != 'nan') &
                            (gdf_all['Sub_Name'].astype(str) != ''))

    gdf_all['has_bc_conn'] = ((gdf_all['BC_Type'] is not None) &
                              (gdf_all['BC_Type'].astype(str) != 'None') &
                              (gdf_all['BC_Type'].astype(str) != 'nan') &
                              (gdf_all['BC_Type'].astype(str) != ''))

    gdf_all['has_inlet'] = ((gdf_all['Inlet'] is not None) &
                            (gdf_all['Inlet'].astype(str) != 'None') &
                            (gdf_all['Inlet'].astype(str) != 'nan') &
                            (gdf_all['Inlet'].astype(str) != ''))

    # feedback.pushInfo(gdf_all.describe().to_string(col_space=[30] * len(gdf_all.describe().columns)))
    # feedback.pushInfo(gdf_all.to_string(col_space=[30] * len(gdf_all.columns)))

    # Set the attributes for custom inlets
    subcatch_outlet = (gdf_all['is_outlet'])
    inlets = (gdf_all['has_inlet'])
    nodes_w_bc = (gdf_all['has_bc_conn'] & ~inlets)
    nodes_no_bc = (~nodes_w_bc & ~inlets)

    n_inlets = sum(inlets)
    n_nodes_w_bc = sum(nodes_w_bc)
    n_nodes_no_bc = sum(nodes_no_bc)

    feedback.pushInfo('Node counts')
    feedback.pushInfo(f'  Subcatchment outlets: {sum(subcatch_outlet)}')
    feedback.pushInfo(f'  Inlets: {n_inlets}')
    feedback.pushInfo(f'  at BC: {n_nodes_w_bc}')
    feedback.pushInfo(f'  no 2D or subcatchment connection: {n_nodes_no_bc}')
    feedback.pushInfo(f'\n\n\n')

    if initialize_ymax:
        gdf_all['Ymax'] = 0.0

    # Inlets
    if n_inlets:
        gdf_all.loc[inlets, 'Ysur'] = inlet_ysur
        gdf_all.loc[inlets, 'Apond'] = inlet_apond
        if ymax_from_inlet_elev:
            gdf_all.loc[inlets, 'Ymax'] = gdf_all.loc[inlets, 'Elevation'] - gdf_all.loc[inlets, 'Elev']

    # nodes at BC
    if n_nodes_w_bc:
        gdf_all.loc[nodes_w_bc, 'Ysur'] = hx_ysur
        gdf_all.loc[nodes_w_bc, 'Apond'] = hx_apond

    # nodes with no BC
    if n_nodes_no_bc:
        gdf_all.loc[nodes_no_bc, 'Ysur'] = no_conn_ysur
        gdf_all.loc[nodes_no_bc, 'Apond'] = no_conn_apond

    # Subcatchment outflows - do last to overwrite anything previous
    if no_ponding_for_subcatch_nodes:
        gdf_all.loc[subcatch_outlet, 'Ysur'] = 0.0
        gdf_all.loc[subcatch_outlet, 'Apond'] = 0.0

    return gdf_all


def set_junction_atts(features_junctions,
                      lays_subcatch,
                      lays_inlet_usage,
                      lays_bc_conn,
                      output_layer,
                      inlet_ysur,
                      inlet_apond,
                      hx_ysur,
                      hx_apond,
                      no_conn_ysur,
                      no_conn_apond,
                      feedback=ScreenProcessingFeedback()):
    dp = output_layer.dataProvider()
    output_layer.startEditing()
    dp.addAttributes([
        QgsField("Name", QVariant.String),
        QgsField("Elev", QVariant.Double),
        QgsField("Ymax", QVariant.Double),
        QgsField("Y0", QVariant.Double),
        QgsField("Ysur", QVariant.Double),
        QgsField("Apond", QVariant.Double),
    ])
    output_layer.updateFields()

    gdf_junct = gpd.GeoDataFrame.from_features(features_junctions)

    gdf_inlet_usage = None
    if lays_inlet_usage is not None:
        gdfs_inlet_usage = []
        for lay_inlet_usage in lays_inlet_usage:
            gdfs_inlet_usage.append(gpd.GeoDataFrame.from_features(lay_inlet_usage.getFeatures()))

        gdf_inlet_usage = pd.concat(gdfs_inlet_usage, axis=0)
        gdf_inlet_usage = gdf_inlet_usage[['geometry', 'Inlet', 'Elevation']]

    gdfs_bc_conn = []
    for lay_bc_conn in lays_bc_conn:
        gdfs_bc_conn.append(gpd.GeoDataFrame.from_features(lay_bc_conn.getFeatures()))

    gdf_bc_conn = None
    if len(gdfs_bc_conn) > 0:
        gdf_bc_conn = pd.concat(gdfs_bc_conn, axis=0)
        gdf_bc_conn = gdf_bc_conn[['geometry', 'Type']].rename(columns={'Type': 'BC_Type'})

    # feedback.pushInfo(gdf_bc_conn.to_string(col_space=[30] * len(gdf_bc_conn.columns)))

    gdfs_subcatch = []
    for lay_subcatch in lays_subcatch:
        gdfs_subcatch.append(gpd.GeoDataFrame.from_features(lay_subcatch.getFeatures()))

    gdf_subcatch = None
    if len(gdfs_subcatch) > 0:
        gdf_subcatch = pd.concat(gdfs_subcatch, axis=0)
        gdf_subcatch = gdf_subcatch[['Name', 'Outlet']].rename(
            columns={
                'Name': 'Sub_Name',
                'Outlet': 'Sub_Outlet',
            }
        )

    gdf_junct_inlets = gpd.sjoin(gdf_junct,
                                 gdf_inlet_usage,
                                 how='left',
                                 predicate='intersects',
                                 rsuffix='_in')

    if gdf_bc_conn is not None:
        gdf_all = gpd.sjoin_nearest(gdf_junct_inlets,
                                    gdf_bc_conn[['geometry', 'BC_Type']],
                                    how='left',
                                    max_distance=0.001,
                                    rsuffix='_bc_conn')
        gdf_all = gdf_all.drop_duplicates(subset='Name')
    else:
        gdf_all = gdf_junct_inlets
        gdf_all['geometry_bc_conn'] = None
        gdf_all['BC_Type'] = None

    if gdf_subcatch is not None:
        gdf_all = gdf_all.merge(gdf_subcatch,
                                how='left',
                                left_on='Name',
                                right_on='Sub_Outlet')
    else:
        gdf_all['Sub_Name'] = None

    feedback.pushInfo(gdf_all.to_string(col_space=[30] * len(gdf_all.columns)))

    gdf_all['is_outlet'] = ((gdf_all['Sub_Name'] is not None) &
                            (gdf_all['Sub_Name'].astype(str) != 'None') &
                            (gdf_all['Sub_Name'].astype(str) != 'nan') &
                            (gdf_all['Sub_Name'].astype(str) != ''))

    gdf_all['has_bc_conn'] = ((gdf_all['BC_Type'] is not None) &
                              (gdf_all['BC_Type'].astype(str) != 'None') &
                              (gdf_all['BC_Type'].astype(str) != 'nan') &
                              (gdf_all['BC_Type'].astype(str) != ''))

    gdf_all['has_inlet'] = ((gdf_all['Inlet'] is not None) &
                            (gdf_all['Inlet'].astype(str) != 'None') &
                            (gdf_all['Inlet'].astype(str) != 'nan') &
                            (gdf_all['Inlet'].astype(str) != ''))

    # feedback.pushInfo(gdf_all.describe().to_string(col_space=[30] * len(gdf_all.describe().columns)))
    # feedback.pushInfo(gdf_all.to_string(col_space=[30] * len(gdf_all.columns)))

    # Set the attributes for custom inlets
    subcatch_outlet = (gdf_all['is_outlet'])
    inlets = (gdf_all['has_inlet'] & ~subcatch_outlet)
    nodes_w_bc = (gdf_all['has_bc_conn'] & ~inlets & ~subcatch_outlet)
    nodes_no_bc = (~nodes_w_bc & ~inlets & ~subcatch_outlet)

    feedback.pushInfo('Node counts')
    feedback.pushInfo(f'  Subcatchment outlets: {sum(subcatch_outlet)}')
    feedback.pushInfo(f'  Inlets: {sum(inlets)}')
    feedback.pushInfo(f'  at BC: {sum(nodes_w_bc)}')
    feedback.pushInfo(f'  no 2D or subcatchment connection: {sum(nodes_no_bc)}')
    feedback.pushInfo(f'\n\n\n')

    # Subcatchment outflows
    gdf_all.loc[subcatch_outlet, 'Ysur'] = 0.0
    gdf_all.loc[subcatch_outlet, 'Apond'] = 0.0

    # Inlets
    gdf_all.loc[inlets, 'Ysur'] = inlet_ysur
    gdf_all.loc[inlets, 'Apond'] = inlet_apond

    # nodes at BC
    gdf_all.loc[nodes_w_bc, 'Ysur'] = hx_ysur
    gdf_all.loc[nodes_w_bc, 'Apond'] = hx_apond

    # nodes with no BC
    gdf_all.loc[nodes_no_bc, 'Ysur'] = no_conn_ysur
    gdf_all.loc[nodes_no_bc, 'Apond'] = no_conn_apond

    features_to_add = []

    gdf_all.apply(lambda x: create_junction_features(x, output_layer, features_to_add),
                  axis=1)

    dp.addFeatures(features_to_add)

    output_layer.updateExtents()
    output_layer.commitChanges()

    return output_layer
