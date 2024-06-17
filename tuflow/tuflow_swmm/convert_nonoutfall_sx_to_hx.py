import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely import LineString
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def convert_nonoutfall_sx_to_hx_gdfs(
        gdf_swmm_nodes: gpd.GeoDataFrame,
        gdf_bc: gpd.GeoDataFrame,
        gdf_inlets: gpd.GeoDataFrame | None,
        feedback=ScreenProcessingFeedback(),
) -> gpd.GeoDataFrame:
    feedback.pushInfo(f'Number of SWMM Nodes: {len(gdf_swmm_nodes)}.')

    # if we have inlets, neglect nodes with inlets (these use SX connections)
    if gdf_inlets is not None:
        gdf_swmm_nodes = gdf_swmm_nodes.overlay(gdf_inlets, how='difference')
        feedback.pushInfo(f'Number of SWMM Nodes without inlets: {len(gdf_swmm_nodes)}')

    # Move fid, geometry columns to the end
    cols_to_move = {'fid', 'geometry'}.intersection(set(gdf_bc.columns))
    cols_new = [x for x in gdf_bc.columns if x not in cols_to_move] + list(cols_to_move)
    gdf_bc = gdf_bc[cols_new]

    bc_colnames = ['Type', 'Flags', 'Name', 'f', 'd', 'td', 'a', 'b']

    if len(gdf_bc.columns) < len(bc_colnames) + 1:  # +1 for geometry
        feedback.reportError(f'Not enough columns in BC layer.', fatalError=True)

    feedback.pushInfo(f'Number of BC Polylines: {len(gdf_bc)}.')

    gdf_bc.rename(columns=dict(zip(gdf_bc.columns, bc_colnames)), inplace=True)

    gdf_bc_endpoints = gdf_bc.copy(deep=True)
    gdf_bc_endpoints['endpoint1'] = shapely.get_point(gdf_bc_endpoints.geometry, 0)
    gdf_bc_endpoints['endpoint2'] = shapely.get_point(gdf_bc_endpoints.geometry, 1)
    gdf_bc_endpoints['polyline'] = gdf_bc_endpoints['geometry']

    gdf_bc_lines_endpoint1 = gdf_bc_endpoints.copy(deep=True)
    gdf_bc_lines_endpoint1['Side'] = 1
    gdf_bc_lines_endpoint1['geometry'] = gdf_bc_lines_endpoint1['endpoint1']
    gdf_bc_lines_endpoint2 = gdf_bc_endpoints.copy(deep=True)
    gdf_bc_lines_endpoint2['Side'] = 2
    gdf_bc_lines_endpoint2['geometry'] = gdf_bc_lines_endpoint2['endpoint2']

    gdf_bc_lines_endpoints = pd.concat([gdf_bc_lines_endpoint1, gdf_bc_lines_endpoint2], axis=0)
    gdf_sx_lines_endpoints = gdf_bc_lines_endpoints[gdf_bc_lines_endpoints['Type'].str.lower() == 'sx'].copy(deep=True)
    gdf_cn_lines_endpoints = gdf_bc_lines_endpoints[gdf_bc_lines_endpoints['Type'].str.lower() == 'cn'].copy(deep=True)

    gdf_nodes_cn = gdf_swmm_nodes.sjoin_nearest(gdf_cn_lines_endpoints, max_distance=0.01)

    gdf_nodes_cn['CnOpp'] = gdf_nodes_cn['Side'].apply(lambda x: 1 if x == 2 else 2)

    gdf_nodes_cn['node_loc'] = gdf_nodes_cn['geometry']
    gdf_nodes_cn.loc[gdf_nodes_cn['CnOpp'] == 1, 'geometry'] = gdf_nodes_cn.loc[gdf_nodes_cn['CnOpp'] == 1, 'endpoint1']
    gdf_nodes_cn.loc[gdf_nodes_cn['CnOpp'] == 2, 'geometry'] = gdf_nodes_cn.loc[gdf_nodes_cn['CnOpp'] == 2, 'endpoint2']
    gdf_nodes_cn_sx = gdf_nodes_cn.sjoin_nearest(gdf_sx_lines_endpoints,
                                                 lsuffix='node_sx',
                                                 rsuffix='sx',
                                                 max_distance=0.01)

    # Need to change all the SX lines to HX
    feedback.pushInfo(f'Number of SX polylines to convert to HX: {len(gdf_nodes_cn_sx['index_sx'].unique())}.')
    gdf_bc.loc[gdf_bc.index.isin(gdf_nodes_cn_sx['index_sx'].unique()), 'Type'] = 'HX'

    # Need to add CN lines for missing SX sides to node
    sx_index_side = gdf_nodes_cn_sx[['index_sx', 'Side_sx']]
    # see which ones are full (have connections on both sides)
    sx_index_side = sx_index_side.groupby('index_sx').agg('count')
    sx_index_full = sx_index_side[sx_index_side['Side_sx'] == 2].index.to_list()

    gdf_nodes_cn_sx = gdf_nodes_cn_sx[~gdf_nodes_cn_sx['index_sx'].isin(sx_index_full)]
    gdf_nodes_cn_sx['SxOpp'] = gdf_nodes_cn_sx['Side_sx'].apply(lambda x: 1 if x == 1 else 2)
    gdf_nodes_cn_sx['pt1'] = np.where(gdf_nodes_cn_sx['Side_sx'] == 1,
                                      gdf_nodes_cn_sx['endpoint2_sx'],
                                      gdf_nodes_cn_sx['endpoint1_sx'])
    gdf_nodes_cn_sx['pt2'] = gdf_nodes_cn_sx['node_loc']
    gdf_nodes_cn_sx['geometry'] = gdf_nodes_cn_sx.apply(lambda row: LineString([row['pt1'], row['pt2']]), axis=1)
    gdf_nodes_cn_sx['Name'] = ''
    gdf_nodes_cn_sx['Type'] = 'CN'
    gdf_nodes_cn_sx['Flags'] = ''
    gdf_nodes_cn_sx.loc[:, ['f', 'd', 'td', 'a', 'b']] = None

    gdf_new_cn = gdf_nodes_cn_sx[['Type', 'Flags', 'Name', 'f', 'd', 'td', 'a', 'b', 'geometry']].copy(deep=True)
    feedback.pushInfo(f'Adding {len(gdf_new_cn)} new CN lines to connect converted HX polylines.')

    gdf_bc = gpd.GeoDataFrame(pd.concat([gdf_bc, gdf_new_cn], axis=0))

    # if it exists move fid column back to the front
    if 'fid' in gdf_bc:
        new_cols = ['fid'] + [x for x in gdf_bc.columns if x != 'fid']
        gdf_bc = gdf_bc[new_cols]

    return gdf_bc


def convert_nonoutfall_sx_to_hx(
        swmm_gpkg: str,
        bc_in_filename: str,
        bc_in_layername: str | None,
        inlet_usage_file_layernames: list[tuple[str, str]],
        bc_out_filename: str,
        bc_out_layername: str | None,
        feedback=ScreenProcessingFeedback()
):
    node_layers = ['Nodes--Storage', 'Nodes--Junctions', 'Nodes--Dividers']

    swmm_layers = fiona.listlayers(str(swmm_gpkg))

    swmm_node_layers = list(set(node_layers).intersection(set(swmm_layers)))

    feedback.pushInfo(f'Reading SWMM Node Layers from file: {swmm_gpkg}.')
    gdfs_swmm = [gpd.read_file(swmm_gpkg, layer=nl) for nl in swmm_node_layers]

    gdf_swmm_nodes = gpd.GeoDataFrame(pd.concat([x[['Name', 'geometry']] for x in gdfs_swmm], axis=0))
    feedback.pushInfo(f'Number of SWMM Nodes: {len(gdf_swmm_nodes)}.')

    feedback.pushInfo(f'\nReading BC layer from file: {bc_in_filename}.')
    gdf_bc = gpd.read_file(bc_in_filename, layer=bc_in_layername)

    gdf_inlets = None
    if len(inlet_usage_file_layernames) > 0:
        gdfs_inlets = []
        for filename, layername in inlet_usage_file_layernames:
            gdfs_inlets.append(gpd.read_file(filename, layer=layername)[['Inlet', 'geometry']])
        gdf_inlets = pd.concat(gdfs_inlets)

    gdf_bc = convert_nonoutfall_sx_to_hx_gdfs(
        gdf_swmm_nodes,
        gdf_bc,
        gdf_inlets,
    )

    gdf_bc.to_file(bc_out_filename, layer=bc_out_layername)
