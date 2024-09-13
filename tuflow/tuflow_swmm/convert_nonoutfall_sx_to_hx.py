import fiona
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely import LineString
from tuflow.tuflow_swmm.bc_conn_util import find_nodes_with_bc_conn, BcOption
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

    gdf_nodes_cn_sx = find_nodes_with_bc_conn(
        gdf_swmm_nodes,
        gdf_bc,
        BcOption.SX,
        feedback,
    )

    # Need to change all the SX lines to HX
    num_sx_to_hx = len(gdf_nodes_cn_sx['index_bc'].unique())
    feedback.pushInfo(f'Number of SX polylines to convert to HX: {num_sx_to_hx}.')

    if num_sx_to_hx > 0:
        gdf_bc.loc[gdf_bc.index.isin(gdf_nodes_cn_sx['index_bc'].unique()), 'Type'] = 'HX'

        # Need to add CN lines for missing SX sides to node
        sx_index_side = gdf_nodes_cn_sx[['index_bc', 'Side']]
        # see which ones are full (have connections on both sides)
        sx_index_side = sx_index_side.groupby('index_bc').agg('count')
        sx_index_full = sx_index_side[sx_index_side['Side'] == 2].index.to_list()

        gdf_nodes_cn_sx = gdf_nodes_cn_sx[~gdf_nodes_cn_sx['index_bc'].isin(sx_index_full)]
        # gdf_nodes_cn_sx['SxOpp'] = gdf_nodes_cn_sx['Side'].astype(int).apply(lambda x: 1 if x == 2 else 2)
        gdf_nodes_cn_sx.loc[:, 'pt1'] = gdf_nodes_cn_sx.loc[:, ['hxsx_side', 'geom_hxsx']].apply(
            lambda x: shapely.get_point(x['geom_hxsx'], -1) if x['hxsx_side'] == 1 else shapely.get_point(x['geom_hxsx'], 0),
            axis=1
        )
        #gdf_nodes_cn_sx['pt1'] = np.where(gdf_nodes_cn_sx['hxsx_side'] == 1,
        #                                  shapely.get_point(gdf_nodes_cn_sx['geom_hxsx'], 0),
        #                                  shapely.get_point(gdf_nodes_cn_sx['geom_hxsx'], -1))
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
