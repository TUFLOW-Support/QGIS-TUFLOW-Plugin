has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    gpd = None
import math
import numpy as np
import pandas as pd
from pathlib import Path

try:
    from shapely.geometry import LineString
    from shapely import get_coordinates, get_point
    has_shapely = True
except ImportError:
    has_shapely = False
    LineString = 'LineString'

from tuflow.tuflow_swmm.bc_conn_util import find_nodes_with_bc_conn, BcOption
from tuflow.tuflow_swmm.convert_nonoutfall_sx_to_hx import convert_nonoutfall_sx_to_hx_gdfs
from tuflow.tuflow_swmm.geom_util import get_offset_point_at_angle
from tuflow.tuflow_swmm.gis_list_layers import get_gis_layers
from tuflow.tuflow_swmm.layer_util import increment_layer, read_and_concat_layers
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)


def last_segment_vector_normalized(row):
    coords = row['geometry_y'].coords
    vector = [coords[-1][0] - coords[-2][0], coords[-1][1] - coords[-2][1]]
    length = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])
    vector_norm = (vector[0] / length, vector[1] / length)

    return vector_norm


def create_dummy_conduits(names, from_nodes, to_nodes, lengths, geoms, crs):
    if len(names) == 0:
        return None

    gdf_dummy_conduits = gpd.GeoDataFrame(
        data={
            'Name': names,
            'From Node': from_nodes,
            'To Node': to_nodes,
            'Length': lengths,
            'Roughness': [0.015] * len(names),
            'InOffset': [0.0] * len(names),
            'OutOffset': [0.0] * len(names),
            'InitFlow': [0.0] * len(names),
            'xsec_XsecType': ['Dummy'] * len(names),
            'xsec_Geom1': [0.0] * len(names),
            'xsec_Geom2': [0.0] * len(names),
            'xsec_Geom3': [0.0] * len(names),
            'xsec_Geom4': [0.0] * len(names),
            'xsec_Barrels': [1] * len(names),
        },
        geometry=geoms,
        crs=crs,
    )
    return gdf_dummy_conduits


def create_offset_node_and_extend_conduits(
        gdf_nodes_to_offset,
        gdf_all_links,
        suffix,
        are_storage_nodes,
        are_outfall_nodes,
        offset_distance,
        offset_orig_node=False,
):
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: create_offset_node_and_extend_conduits().')

    # find links (junctions downstream, outfalls upstream)
    merge_field = 'To Node' if are_outfall_nodes else 'From Node'
    gdf_links_for_junctions_to_extend = gdf_all_links.merge(
        gdf_nodes_to_offset,
        how='right',
        left_on=merge_field,
        right_on='Name',
        suffixes=('_link', '_node'),
    )

    angle = 135.0
    if are_outfall_nodes:
        if offset_orig_node:
            angle = 180.0
        else:
            angle = 45.0

    offset_pt_geoms = gdf_links_for_junctions_to_extend['geometry_link'].apply(
        lambda x: get_offset_point_at_angle(x, offset_distance, angle, not are_outfall_nodes)
    )
    orig_pts = gdf_nodes_to_offset['geometry']

    gdf_junction_inflows = gdf_nodes_to_offset.copy(deep=True)
    if offset_orig_node:
        gdf_junction_inflows['OrigName'] = gdf_junction_inflows['Name']
        gdf_junction_inflows['Name'] = gdf_junction_inflows['Name']
    else:
        gdf_junction_inflows['OrigName'] = gdf_junction_inflows['Name']
        gdf_junction_inflows['Name'] = gdf_junction_inflows['Name'] + f'_{suffix}'
    gdf_junction_inflows['geometry'] = orig_pts if offset_orig_node else offset_pt_geoms.values
    if are_storage_nodes or are_outfall_nodes:
        gdf_junction_inflows.loc[:, ['Ymax', 'Y0', 'Ysur']] = 0.0
        gdf_junction_inflows.loc[:, ['Apond']] = 5.0
        gdf_junction_inflows.loc[:, ['Tag', 'Description']] = None
        gdf_junction_inflows = gdf_junction_inflows[
            [
                'Name',
                'Elev',
                'Ymax',
                'Y0',
                'Ysur',
                'Apond',
                'Tag',
                'Description',
                'OrigName',
                'geometry',
            ]
        ]

    # create dummy conduits from the inflow nodes to the original nodes
    names = gdf_nodes_to_offset['Name'] + f'_{suffix}'
    from_nodes = names
    to_nodes = gdf_nodes_to_offset['Name']

    if offset_orig_node:
        gdf_nodes_to_offset['pt1'] = orig_pts.values
        gdf_nodes_to_offset['pt2'] = offset_pt_geoms.values

        gdf_nodes_to_offset.loc[:, 'geometry'] = gdf_nodes_to_offset['pt2']

        from_nodes = gdf_nodes_to_offset['Name'].copy(deep=True)
        gdf_nodes_to_offset['OrigName'] = gdf_nodes_to_offset['Name']
        gdf_nodes_to_offset.loc[:, 'Name'] = gdf_nodes_to_offset['Name'] + f'_{suffix}'
        to_nodes = gdf_nodes_to_offset['Name']
    else:
        gdf_nodes_to_offset['pt1'] = offset_pt_geoms.values
        gdf_nodes_to_offset['pt2'] = orig_pts.values

    geoms = gdf_nodes_to_offset.apply(lambda x: LineString([x['pt1'], x['pt2']]), axis=1)
    gdf_dummy_conduits = create_dummy_conduits(
        names,
        from_nodes,
        to_nodes,
        [offset_distance] * len(names),
        geoms,
        gdf_all_links.crs
    )

    return gdf_junction_inflows, gdf_dummy_conduits


def move_inflow_nodes(
        gdf_bc_inflows,
        gdf_new_junctions,
):
    gdf_bc_inflows_extensions = gdf_bc_inflows.merge(
        gdf_new_junctions,
        how='left',
        left_on='Node',
        right_on='OrigName',
        suffixes=('_bc', '_inflows')
    )
    gdf_bc_inflows_extensions['Node'] = np.where(gdf_bc_inflows_extensions['Name'].isnull(),
                                                 gdf_bc_inflows_extensions['Node'],
                                                 gdf_bc_inflows_extensions['Name'])
    gdf_bc_inflows_extensions['geometry'] = np.where(gdf_bc_inflows_extensions['geometry_inflows'].isnull(),
                                                     gdf_bc_inflows_extensions['geometry_bc'],
                                                     gdf_bc_inflows_extensions['geometry_inflows'])
    columns_to_drop = set(gdf_bc_inflows_extensions.columns) - set(gdf_bc_inflows.columns)
    gdf_bc_inflows_extensions = gdf_bc_inflows_extensions.drop(columns=columns_to_drop)

    return gdf_bc_inflows_extensions


def shift_bc_line_002(geometry, nodept1, nodept2):
    if not has_shapely:
        raise Exception('Shapely not installed and is required for function: shift_bc_line_002().')

    out_geom = geometry
    if get_point(out_geom, 0).equals_exact(nodept1, 1e-4):
        coords = get_coordinates(out_geom)
        coords[0] = nodept2.coords[0]
        new_linestring = LineString(coords)
        return new_linestring

    if get_point(out_geom, -1).equals_exact(nodept1, 1e-4):
        coords = get_coordinates(out_geom)
        coords[-1] = nodept2.coords[0]
        new_linestring = LineString(coords)
        return new_linestring
    return out_geom


def shift_sx_connections(gdf_orig_nodes,
                         gdf_shifted_nodes,
                         gdfs_bcs):
    gdfs_bcs_modified = []

    gdf_shifted_nodes = gdf_shifted_nodes.copy(deep=True)

    for gdf_bc in gdfs_bcs:
        # shifted_nodes pt1 will be original location and pt2 will be new location

        gdf_nodes_with_sx = find_nodes_with_bc_conn(
            gdf_orig_nodes[gdf_orig_nodes['Name'].isin(gdf_shifted_nodes['OrigName'])],
            gdf_bc,
            BcOption.SX
        ).copy(deep=True)[['endpoint1', 'endpoint2', 'geometry']]
        gdf_nodes_with_sx['geometry'] = gdf_nodes_with_sx['endpoint1']
        if len(gdf_nodes_with_sx) == 0:
            gdfs_bcs_modified.append(None)
            continue
        # Shift the bc from the original node to the new node
        gdf_bc_out = gdf_bc.copy(deep=True).reset_index(drop=True)

        gdf_shifted_nodes['geometry'] = gdf_shifted_nodes['pt1']
        gdf_bc_out_to_shift = gdf_bc_out.sjoin(gdf_shifted_nodes, how='inner', predicate='touches')
        print(gdf_bc_out_to_shift)

        new_geom = gdf_bc_out_to_shift.loc[:, ['geometry', 'pt1', 'pt2']].apply(
            lambda x: shift_bc_line_002(x['geometry'], x['pt1'], x['pt2']),
            axis=1
        )
        print(gdf_bc_out.loc[75, :])
        gdf_bc_out.loc[new_geom.index, 'geometry'] = new_geom
        print(gdf_bc_out.loc[75, :])
        print(gdf_bc_out)

        gdfs_bcs_modified.append(gdf_bc_out)

        print(pd.concat([gdf_bc, gdf_bc_out]).drop_duplicates(keep=False))

    return gdfs_bcs_modified


def fix_invalid_bc_connections_gdf(
        gdf_all_links,
        gdf_outfalls,
        gdf_junctions,
        gdf_storage,
        gdf_conduits,
        gdf_bc_inflows,
        gdfs_bc_connections,
        gdfs_inlets,
        dummy_chan_length_inflows,
        dummy_chan_length_outfalls,
        offsets_are_elevations,
        feedback,
):
    """
    This function fixes:
    1. SX connections improperly connected to junction or storage nodes without inlets (need to use HX)
    2. SWMM inflows at nodes connected to HX boundaries
    3. SWMM inflows at outfalls

    2 and 3) new nodes created for BC inflows connected to the original using dummy conduits

    TODO Add tool
    """
    # dictionary with return information
    output_info = {}

    # information we gather along the way
    dummy_conduits_to_concat = []
    gdfs_new_junctions = []

    gdf_bc_inflows_mod = gdf_bc_inflows

    # outfall nodes use SX connections
    gdfs_nonoutfall_nodes = [x for x in
                             [
                                 gdf_junctions,
                                 gdf_storage,
                             ] if x is not None
                             ]
    gdf_nonoutfall_nodes = pd.concat(
        [x[['Name', 'Elev', 'geometry']] for x in gdfs_nonoutfall_nodes]
    )

    gdf_inlets_all = None
    if gdfs_inlets is not None:
        gdf_inlets_all = pd.concat(gdfs_inlets)

    # get default crs
    crs_out = None
    if gdf_nonoutfall_nodes is not None:
        crs_out = gdf_nonoutfall_nodes.crs
    if crs_out is None and gdfs_bc_connections is not None:
        crs_out = gdfs_bc_connections[0].crs

    # Need to convert nonoutfall SX to HX
    gdfs_bc_connections_mod = []
    for gdf_bc in gdfs_bc_connections:
        gdf_bc_mod = convert_nonoutfall_sx_to_hx_gdfs(
            gdf_nonoutfall_nodes,
            gdf_bc,
            gdf_inlets_all,
            feedback,
        )
        if gdf_bc_mod is not None:
            gdfs_bc_connections_mod.append(gdf_bc_mod.to_crs(crs_out))
        else:
            gdfs_bc_connections_mod.append(gdf_bc.to_crs(crs_out))

    # Merge bc connections to find connected nodes
    gdf_bc_connections_all = pd.concat(gdfs_bc_connections_mod).reset_index(drop=True)

    # Identify junctions with bc inflows
    if gdf_junctions is not None and gdf_bc_inflows_mod is not None:
        junction_has_inflows = gdf_junctions.loc[:, 'Name'].isin(gdf_bc_inflows_mod['Node'])
        feedback.pushInfo(f'{junction_has_inflows.sum()} junctions have inflows')

        # We want to find all the junctions to HX connections and inflows
        # noinspection PyTypeChecker
        gdf_nodes_cn_hx = find_nodes_with_bc_conn(gdf_junctions, gdf_bc_connections_all, BcOption.HX)
        junction_has_hx = gdf_junctions.loc[:, 'Name'].isin(gdf_nodes_cn_hx['Name_left'].unique())
        feedback.pushInfo(f'{junction_has_hx.sum()} junctions have HX boundaries')

        junctions_with_inflows_and_hx = junction_has_inflows & junction_has_hx
        feedback.pushInfo(f'{junctions_with_inflows_and_hx.sum()} junctions have inflows and HX connections.')

        if junctions_with_inflows_and_hx.sum() > 0:
            # Add an inflow node upstream of junction at the same elevation
            # find links that starts at the junction (should be an outfall if at the end)
            gdf_junctions_to_extend = gdf_junctions[junctions_with_inflows_and_hx].copy(deep=True)
            gdf_junction_inflows, gdf_dummy_conduits = create_offset_node_and_extend_conduits(
                gdf_junctions_to_extend,
                gdf_all_links,
                'in',
                False,
                False,
                dummy_chan_length_inflows,
            )

            gdf_bc_inflows_extensions = move_inflow_nodes(
                gdf_bc_inflows_mod,
                gdf_junction_inflows,
            )

            dummy_conduits_to_concat.append(gdf_dummy_conduits)
            gdfs_new_junctions.append(gdf_junction_inflows)
            gdf_bc_inflows_mod = gdf_bc_inflows_extensions

    # Identify storage nodes with bc inflows
    # default values
    if gdf_storage is not None and gdf_bc_inflows_mod is not None:
        storage_has_inflows = gdf_storage.loc[:, 'Name'].isin(gdf_bc_inflows_mod['Node'])
        feedback.pushInfo(f'{storage_has_inflows.sum()} storage nodes have inflows')

        # We want to find all the junctions to HX connections and inflows
        gdf_storage_cn_hx = find_nodes_with_bc_conn(gdf_storage, gdf_bc_connections_all, BcOption.HX)
        storage_has_hx = gdf_storage.loc[:, 'Name'].isin(gdf_storage_cn_hx['Name_left'].unique())
        feedback.pushInfo(f'{storage_has_hx.sum()} storage nodes have HX boundaries')

        storage_with_inflows_and_hx = storage_has_inflows & storage_has_hx
        feedback.pushInfo(f'{storage_with_inflows_and_hx.sum()} storage nodes have inflows and HX connections.')

        if storage_with_inflows_and_hx.sum() > 0:
            # Add an inflow node upstream of junction at the same elevation
            # find links that starts at the junction (should be an outfall if at the end)
            gdf_storage_to_extend = gdf_storage[storage_with_inflows_and_hx].copy(deep=True)
            gdf_storage_inflows, gdf_storage_dummy_conduits = create_offset_node_and_extend_conduits(
                gdf_storage_to_extend,
                gdf_all_links,
                'in',
                True,
                False,
                dummy_chan_length_inflows,
            )

            gdf_bc_storage_inflows_extensions = move_inflow_nodes(
                gdf_bc_inflows_mod,
                gdf_storage_inflows,
            )

            dummy_conduits_to_concat.append(gdf_storage_dummy_conduits)
            gdfs_new_junctions.append(gdf_storage_inflows)
            gdf_bc_inflows_mod = gdf_bc_storage_inflows_extensions

    # Need to handle outfall nodes

    # If an outfall has an inflow, shift it like we did with junctions
    if gdf_bc_inflows_mod is not None:
        outfall_has_inflows = gdf_outfalls.loc[:, 'Name'].isin(gdf_bc_inflows_mod['Node'])
        feedback.pushInfo(f'{outfall_has_inflows.sum()} outfalls have inflows')

        gdf_outfall_junct_ext, gdf_outfall_dummy_conduits = create_offset_node_and_extend_conduits(
            gdf_outfalls[outfall_has_inflows].copy(deep=True),
            gdf_all_links,
            'in',
            False,
            True,
            dummy_chan_length_inflows,
        )
        gdf_bc_inflows_ext_outfalls = move_inflow_nodes(
            gdf_bc_inflows_mod,
            gdf_outfall_junct_ext,
        )

        dummy_conduits_to_concat.append(gdf_outfall_dummy_conduits)
        gdfs_new_junctions.append(gdf_outfall_junct_ext)
        gdf_bc_inflows_mod = gdf_bc_inflows_ext_outfalls
    else:
        outfall_has_inflows = pd.Series([False]*len(gdf_outfalls), index=gdf_outfalls.index)

    # - move downstream and put add a junction at the previous location
    # Move any SX connections with the outfall
    # Connect the nodes with a dummy conduit

    # if an outfall was connected to an inlet node or HX lines it needs to be shifted downstream
    gdf_outfalls_cn_hx = find_nodes_with_bc_conn(gdf_outfalls, gdf_bc_connections_all, BcOption.HX)
    outfall_has_hx = gdf_outfalls.loc[:, 'Name'].isin(gdf_outfalls_cn_hx['Name_left'].unique())
    feedback.pushInfo(f'{outfall_has_hx.sum()} outfalls have HX boundaries')

    gdf_outfalls_to_shift = gdf_outfalls[outfall_has_hx | outfall_has_inflows].copy(deep=True)
    if len(gdf_outfalls_to_shift) > 0:
        gdf_outfall_down_ext, gdf_outfall_down_dummy_conduits = create_offset_node_and_extend_conduits(
            gdf_outfalls_to_shift,
            gdf_all_links,
            'ext',
            False,
            True,
            dummy_chan_length_outfalls,
            True,
        )
        gdfs_bc_connections_mod = shift_sx_connections(gdf_outfalls, gdf_outfalls_to_shift, gdfs_bc_connections_mod)
        # Copy modifications back
        gdf_outfalls.loc[gdf_outfalls_to_shift.index, 'geometry'] = gdf_outfalls_to_shift['geometry'].values
        gdf_outfalls.loc[gdf_outfalls_to_shift.index, 'Name'] = gdf_outfalls_to_shift['Name'].values

        dummy_conduits_to_concat.append(gdf_outfall_down_dummy_conduits)
        gdfs_new_junctions.append(gdf_outfall_down_ext)

    # Need to combine dummy conduits
    dummy_conduits_to_concat = [x for x in dummy_conduits_to_concat if x is not None]
    if len(dummy_conduits_to_concat) > 0:
        gdf_dummy_conduits_all = pd.concat(dummy_conduits_to_concat)
    else:
        gdf_dummy_conduits_all = None

    # Need elevations for all nodes
    gdfs_nodes = [x for x in
                  [
                      gdf_junctions,
                      gdf_storage,
                      gdf_outfalls,
                  ] + gdfs_new_junctions if x is not None
                  ]
    gdf_nodes_all = pd.concat(
        [x[['Name', 'Elev']] for x in gdfs_nodes]
    )

    if offsets_are_elevations and gdf_dummy_conduits_all is not None:
        # Need to get the elevations from adjacent nodes
        gdf_dummy_conduits_all.loc[:, 'InOffset'] = gdf_dummy_conduits_all.loc[:, 'From Node'].apply(
            lambda x: gdf_nodes_all.loc[(gdf_nodes_all['Name'] == x), 'Elev'].iloc[0]
        )
        gdf_dummy_conduits_all.loc[:, 'OutOffset'] = gdf_dummy_conduits_all.loc[:, 'To Node'].apply(
            lambda x: gdf_nodes_all.loc[(gdf_nodes_all['Name'] == x), 'Elev'].iloc[0]
        )

    output_info['Modified_junctions'] = pd.concat([gdf_junctions] + gdfs_new_junctions)
    output_info['Modified_conduits'] = pd.concat([gdf_conduits, gdf_dummy_conduits_all])
    output_info['Modified_bc_inflows'] = gdf_bc_inflows_mod
    output_info['Modified_outfalls'] = gdf_outfalls
    output_info['Modified_bc_connections'] = gdfs_bc_connections_mod

    return output_info


def fix_invalid_bc_connections(input_gpkg,
                               output_gpkg,
                               dummy_chan_length_inflows,
                               dummy_chan_legnth_outfalls,
                               gdfs_bc_connections,
                               offsets_are_elevations,
                               output_bc_files_and_layers,
                               gdfs_inlets,
                               feedback=ScreenProcessingFeedback()):
    if not has_gpd:
        message = (
            'This tool requires geopandas: to install please follow instructions on the following webpage: '
            'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    feedback.pushInfo("Fixing invalid BC connections")

    # Remove output geopackage if exists
    Path(output_gpkg).unlink(missing_ok=True)

    if 'Nodes--Junctions' in get_gis_layers(input_gpkg):
        gdf_junctions = gpd.read_file(input_gpkg, layer='Nodes--Junctions')
    else:
        gdf_junctions = None

    if 'Nodes--Storage' in get_gis_layers(input_gpkg):
        gdf_storage = gpd.read_file(input_gpkg, layer='Nodes--Storage')
    else:
        gdf_storage = None

    gdf_conduits = gpd.read_file(input_gpkg, layer='Links--Conduits')

    alt_link_layers = [
        'Links--Pumps',
        'Links--Orifices',
        'Links--Weirs',
        'Links--Outlets',
    ]

    gdf_all_links = read_and_concat_layers(input_gpkg, alt_link_layers, [gdf_conduits])

    gdf_outfalls = None
    if 'Nodes--Outfalls' in get_gis_layers(input_gpkg):
        gdf_outfalls = gpd.read_file(input_gpkg, layer='Nodes--Outfalls')

    gdf_bc_inflows = None
    if 'BC--Inflows' in get_gis_layers(input_gpkg):
        gdf_bc_inflows = gpd.read_file(input_gpkg, layer='BC--Inflows')

    output_info = fix_invalid_bc_connections_gdf(
        gdf_all_links,
        gdf_outfalls,
        gdf_junctions,
        gdf_storage,
        gdf_conduits,
        gdf_bc_inflows,
        gdfs_bc_connections,
        gdfs_inlets,
        dummy_chan_length_inflows,
        dummy_chan_legnth_outfalls,
        offsets_are_elevations,
        feedback,
    )

    modified_layers = [
        'Nodes--Junctions',
        'Nodes--Outfalls',
        'Links--Conduits',
        'BC--Inflows',
    ]

    all_layers = get_gis_layers(input_gpkg)

    layers_to_copy = list(set(all_layers) - set(modified_layers))

    for layername in layers_to_copy:
        gdf_layer = gpd.read_file(input_gpkg, layer=layername)
        gdf_layer.to_file(output_gpkg, layer=layername)

    # Need to copy unmodified layers to new file
    feedback.pushInfo(f'Writing modified SWMM GeoPackage: {output_gpkg}')

    if output_info['Modified_junctions'] is not None:
        output_info['Modified_junctions'].to_file(output_gpkg, layer='Nodes--Junctions')
    if output_info['Modified_outfalls'] is not None:
        output_info['Modified_outfalls'].to_file(output_gpkg, layer='Nodes--Outfalls')
    if output_info['Modified_conduits'] is not None:
        output_info['Modified_conduits'].to_file(output_gpkg, layer='Links--Conduits')
    if output_info['Modified_bc_inflows'] is not None:
        output_info['Modified_bc_inflows'].to_file(output_gpkg, layer='BC--Inflows')

    # Only modified bc files (not None) need to be written
    if output_info['Modified_bc_connections'] is not None:
        for gdf_bc, (output_filename, output_layername) in zip(output_info['Modified_bc_connections'],
                                                               output_bc_files_and_layers):
            if gdf_bc is not None:
                feedback.pushInfo(f'Writing modified bc layer: {output_filename} >> {output_layername}')
                gdf_bc.to_file(output_filename, layer=output_layername)


if __name__ == '__main__':
    swmm_gpkg = Path(r'D:\support\TSC240873\190702_Model\out03\model\swmm\exus77_001.gpkg')

    out_gpkg = swmm_gpkg.with_stem(swmm_gpkg.stem + '_mod')

    dummy_inflows = 10.0
    dummy_outflows = 20.0

    bc_connections_filenames = [
        r'D:\support\TSC240873\190702_Model\out03\model\gis\EX_US77_100yr_gis_layers_1d.gpkg',
        r'D:\support\TSC240873\190702_Model\out03\model\gis\EX_US77_100yr_2d_bc.gpkg'
    ]
    bc_connections_layernames = [
        '2d_bc_swmm_connections',
        'EX_US77_101yr_2d_bc_L'
    ]

    gdfs_bc_connections = [
        gpd.read_file(x, layer=y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
    ]

    output_connection_file_and_layernames = [
        increment_layer(x, y) for x, y in zip(bc_connections_filenames, bc_connections_layernames)
    ]
    print(output_connection_file_and_layernames)

    fix_invalid_bc_connections(swmm_gpkg,
                               out_gpkg,
                               dummy_inflows,
                               dummy_outflows,
                               gdfs_bc_connections,
                               True,
                               [],
                               output_connection_file_and_layernames)
