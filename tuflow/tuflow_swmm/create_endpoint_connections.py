import math
import numpy as np
has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import timeit

from qgis.core import QgsField, QgsGeometry, QgsFeature, QgsPoint, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.compatibility_routines import QT_DOUBLE, QT_STRING, QT_INT


def adjacent_conduits_exist(layer, feat, check_upstream):
    feat_att = 'From Node' if check_upstream else 'To Node'
    adj_att = 'To Node' if check_upstream else 'From Node'

    print(feat_att)
    print(adj_att)

    common_node = feat.attribute(feat_att)
    check_text = f'"{adj_att}" = \'{common_node}\''
    print(check_text)

    # if check_upstream:
    #     adj_features = layer.getFeatures(QgsFeatureRequest().setFilterExpression(
    #         f'"To Node" = \'{common_node}\''
    #     ))
    # else:
    #     adj_features = layer.getFeatures(QgsFeatureRequest().setFilterExpression(
    #         f'"From Node" = \'{common_node}\''
    #     ))

    adj_features = layer.getFeatures(QgsFeatureRequest().setFilterExpression(
        check_text))

    adj_features_exist = False
    for f in adj_features:
        adj_features_exist = True
        break

    return adj_features_exist


def create_connection(layer, seg_points, node_pt, feat_name, feedback):
    conn = QgsFeature(layer.fields())
    conn_geom = QgsGeometry.fromPolyline(
        [
            QgsPoint(seg_points[0, 0], seg_points[0, 1]),
            QgsPoint(node_pt[0], node_pt[1]),
        ]
    )
    validate_errors = conn_geom.validateGeometry()
    if validate_errors:
        feedback.reportError(f'Errors found converting {feat_name}: {validate_errors}', False)

    conn.setGeometry(conn_geom)
    return conn


def create_offset_geom_and_connections(layer, seg_points,
                                       offset_dist, width, num_connections, feat_name, feedback):
    direction = seg_points[0, :] - seg_points[1, :]
    # print(direction)

    length = math.sqrt(np.sum(direction ** 2))
    # print(length)

    dir_norm = direction / length
    # print(dir_norm)

    mid_offset = seg_points[0, :] + dir_norm * offset_dist
    # print(mid_offset)

    perp_norm = np.flip(dir_norm)
    perp_norm[0] = -perp_norm[0]
    pt1 = mid_offset + perp_norm * (width * 0.5)
    pt2 = mid_offset - perp_norm * (width * 0.5)
    # print(pt1)
    # print(pt2)

    new_feat = QgsFeature(layer.fields())
    new_geom = QgsGeometry.fromPolyline(
        [
            QgsPoint(pt1[0], pt1[1]),
            # QgsPoint(mid_offset[0], mid_offset[1]),
            QgsPoint(pt2[0], pt2[1])
        ])
    validate_errors = new_geom.validateGeometry()
    if validate_errors:
        feedback.reportError(f'Errors found converting {feat_name}: {validate_errors}', False)
    new_feat.setGeometry(new_geom)

    connections = [
        create_connection(layer, seg_points, pt1, feat_name, feedback)
    ]

    if num_connections == 2:
        connections.append(create_connection(layer, seg_points, pt2, feat_name, feedback))

    return new_feat, connections


def create_upstream_bc_and_connections(row, layer,
                                       bc_lines, con_lines, offset_distance,
                                       width, number_of_connections, feedback):
    points = np.array((row['geometry'].coords.xy[0],
                       row['geometry'].coords.xy[1])).T
    # print(points)
    feat, conns = create_offset_geom_and_connections(
        layer, points,
        offset_distance, width, number_of_connections,
        row.Name,
        feedback
    )
    bc_lines.append(feat)
    for conn in conns:
        con_lines.append(conn)


def create_downstream_bc_and_connections(row, layer,
                                         bc_lines, con_lines, offset_distance,
                                         width, number_of_connections, feedback):
    points = np.flip(np.array((row['geometry'].coords.xy[-1],
                               row['geometry'].coords.xy[-2])).T)
    # print(points)
    feat, conns = create_offset_geom_and_connections(
        layer, points,
        offset_distance, width, number_of_connections,
        row.Name,
        feedback
    )
    bc_lines.append(feat)
    for conn in conns:
        con_lines.append(conn)


def create_endpoint_connections(input_source,
                                layer_features,
                                offset_dist,
                                width,
                                set_z_flag,
                                output_layer,
                                create_upstream,
                                create_downstream,
                                feedback=ScreenProcessingFeedback()):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    t0 = timeit.default_timer()

    # lay_conduits_mem = QgsVectorLayer(f"LineString?crs={layer.crs}", 'bc_layer', 'memory')
    # dp = lay_conduits_mem.dataProvider()
    dp = output_layer.dataProvider()
    output_layer.startEditing()
    dp.addAttributes([
        QgsField("Type", QT_STRING),
        QgsField("Flags", QT_STRING),
        QgsField("Name", QT_STRING),
        QgsField("f", QT_DOUBLE),
        QgsField("D", QT_DOUBLE),
        QgsField("Td", QT_DOUBLE),
        QgsField("A", QT_DOUBLE),
        QgsField("B", QT_DOUBLE),
    ])
    output_layer.updateFields()

    gdf = gpd.GeoDataFrame.from_features(input_source)
    # print(gdf)
    feedback.pushInfo(f'Generating bc lines using {len(gdf)} features')

    gdf_conduits_layer = gpd.GeoDataFrame.from_features(layer_features)

    # If we don't have any features stop
    if len(gdf) == 0:
        feedback.reportError('No features provided. Aborting.', True)

    feedback.pushInfo(str(gdf_conduits_layer.columns))

    gdf2 = gdf_conduits_layer.merge(gdf_conduits_layer[['From Node']], how='left',
                     left_on='To Node', right_on='From Node',
                     suffixes=(None, '_down'))
    gdf2['HasDownstream'] = ~gdf2['From Node_down'].isnull()

    gdf3 = gdf2.merge(gdf2[['To Node']], how='left',
                      left_on='From Node', right_on='To Node',
                      suffixes=(None, '_up'))
    gdf3['HasUpstream'] = ~gdf3['To Node_up'].isnull()

    # Filter to selected features
    gdf3 = gdf3[gdf3['Name'].isin(gdf['Name'])]

    gdf_no_upstream = gdf3[~gdf3['HasUpstream']].drop_duplicates(subset='From Node')
    gdf_no_downstream = gdf3[~gdf3['HasDownstream']].drop_duplicates(subset='To Node')

    if len(gdf_no_downstream) == 0 and len(gdf_no_upstream) == 0:
        feedback.reportError(
            'No upstream and downstream channels identified. Double-check that the "From Node" and "To Node" fields have been filled in',
            True)

    # t1 = timeit.default_timer()
    # elapsed_time = round((t1 - t0), 3)
    # print(f'Elapsed time: {elapsed_time:0.3f} seconds')

    # HX lines are upstream need two connections
    hx_lines = []
    cn_lines = []

    if create_upstream:
        gdf_no_upstream.apply(create_upstream_bc_and_connections,
                              args=(output_layer,
                                    hx_lines,
                                    cn_lines,
                                    offset_dist,
                                    width,
                                    2,
                                    feedback), axis=1)

    # SX lines are downstream only one connection
    sx_lines = []
    if create_downstream:
        gdf_no_downstream.apply(create_downstream_bc_and_connections,
                                args=(output_layer,
                                      sx_lines,
                                      cn_lines,
                                      offset_dist,
                                      width,
                                      1,
                                      feedback), axis=1)

    for hx_line in hx_lines:
        hx_line.setAttribute('Type', 'HX')
        if set_z_flag:
            hx_line.setAttribute('Flags', 'Z')

    feedback.pushInfo(f'Adding {len(hx_lines)} HX lines to output')
    dp.addFeatures(hx_lines)

    for sx_line in sx_lines:
        sx_line.setAttribute('Type', 'SX')
        if set_z_flag:
            sx_line.setAttribute('Flags', 'Z')

    feedback.pushInfo(f'Adding {len(sx_lines)} SX lines to output')
    dp.addFeatures(sx_lines)

    for cn_line in cn_lines:
        cn_line.setAttribute('Type', 'CN')

    feedback.pushInfo(f'Adding {len(cn_lines)} CN lines to output')
    dp.addFeatures(cn_lines)

    output_layer.updateExtents()
    output_layer.commitChanges()
    # QgsProject.instance().addMapLayer(lay_conduits_mem)

    t1 = timeit.default_timer()
    elapsed_time = round((t1 - t0), 3)
    feedback.pushInfo(f'Elapsed time: {elapsed_time:0.3f} seconds')

    # iface.setActiveLayer(layer)
