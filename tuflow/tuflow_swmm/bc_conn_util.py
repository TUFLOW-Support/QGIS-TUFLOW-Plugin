from enum import Enum
import geopandas as gpd
import pandas as pd
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
import shapely
from shapely import LineString


class BcOption(Enum):
    SX = 1,
    HX = 2,
    BOTH = 3


def find_nodes_with_bc_conn(
        gdf_nodes: gpd.GeoDataFrame,
        gdf_bc: gpd.GeoDataFrame,
        bc_option: BcOption,
        feedback=ScreenProcessingFeedback(),
) -> gpd.GeoDataFrame:
    """
    This function returns a GeoDataFrame containing that contains nodes with the appropriate boundaries.
    Fields: CnSide = 1 or 2 for side of CN line at the node
    """
    # feedback.pushInfo(f'Finding nodes with BC connections: {bc_option.name}')

    # Move fid, geometry columns to the end
    cols_to_move = {'fid', 'geometry'}.intersection(set(gdf_bc.columns))
    cols_new = [x for x in gdf_bc.columns if x not in cols_to_move] + list(cols_to_move)
    gdf_bc = gdf_bc[cols_new]

    bc_colnames = ['Type', 'Flags', 'Name', 'f', 'd', 'td', 'a', 'b']

    if len(gdf_bc.columns) < len(bc_colnames) + 1:  # +1 for geometry
        feedback.reportError(f'Not enough columns in BC layer.', fatalError=True)

    # feedback.pushInfo(f'Number of BC Polylines: {len(gdf_bc)}.')

    gdf_bc.rename(columns=dict(zip(gdf_bc.columns, bc_colnames)), inplace=True)

    gdf_bc_endpoints = gdf_bc.copy(deep=True)
    gdf_bc_endpoints['endpoint1'] = shapely.get_point(gdf_bc_endpoints.geometry, 0)
    gdf_bc_endpoints['endpoint2'] = shapely.get_point(gdf_bc_endpoints.geometry, -1)
    gdf_bc_endpoints['polyline'] = gdf_bc_endpoints['geometry']

    gdf_bc_lines_endpoint1 = gdf_bc_endpoints.copy(deep=True)
    gdf_bc_lines_endpoint1['Side'] = 1
    gdf_bc_lines_endpoint1['geometry'] = gdf_bc_lines_endpoint1['endpoint1']
    gdf_bc_lines_endpoint2 = gdf_bc_endpoints.copy(deep=True)
    gdf_bc_lines_endpoint2['Side'] = 2
    gdf_bc_lines_endpoint2['geometry'] = gdf_bc_lines_endpoint2['endpoint2']

    gdf_bc_lines = gdf_bc.copy(deep=True)
    # print(gdf_bc_lines)
    hx_lines = gdf_bc_lines['Type'].str.lower() == 'hx'
    sx_lines = gdf_bc_lines['Type'].str.lower() == 'sx'

    # print(f'HX lines: {sum(hx_lines)}')
    # print(f'SX lines: {sum(sx_lines)}')

    lines_to_use = hx_lines if bc_option == BcOption.HX else sx_lines if bc_option == BcOption.SX else hx_lines & sx_lines
    gdf_bc_lines_hxsx = gdf_bc_lines[lines_to_use].copy(deep=True)
    # print(f'  Number of HX lines: {len(gdf_bc_lines_hxsx)}')

    gdf_bc_lines_endpoints = pd.concat([gdf_bc_lines_endpoint1, gdf_bc_lines_endpoint2], axis=0)
    # need to see if they intersect anywhere not just endpoints
    # gdf_bc_lines_endpoints_sx = gdf_bc_lines_endpoints[gdf_bc_lines_endpoints['Type'].str.lower() == 'sx'].copy(
    #    deep=True)
    # gdf_bc_lines_endpoints_hx = gdf_bc_lines_endpoints[gdf_bc_lines_endpoints['Type'].str.lower() == 'hx'].copy(
    #    deep=True)
    # gdfs_bc = []
    # if bc_option != BcOption.HX:
    #    gdfs_bc.append(gdf_bc_lines_endpoints_sx)
    # if bc_option != BcOption.SX:
    #    gdfs_bc.append(gdf_bc_lines_endpoints_hx)
    # if len(gdfs_bc) == 1:
    #    gdf_bc_lines_endpoints_hxsx = gdfs_bc[0]
    # else:
    #    gdf_bc_lines_endpoints_hxsx = pd.concat(gdfs_bc)

    gdf_cn_lines_endpoints = gdf_bc_lines_endpoints[gdf_bc_lines_endpoints['Type'].str.lower() == 'cn'].copy(deep=True)

    # print(gdf_cn_lines_endpoints)
    gdf_nodes_cn = gdf_nodes.sjoin(gdf_cn_lines_endpoints,
                                   how='left',
                                   predicate='dwithin',
                                   distance=0.01).copy(deep=True)

    gdf_nodes_cn['CnSide'] = gdf_nodes_cn['Side'].apply(lambda x: 1 if x == 2 else 2)

    gdf_nodes_cn['node_loc'] = gdf_nodes_cn['geometry']
    gdf_nodes_cn.loc[gdf_nodes_cn['CnSide'] == 1, 'geometry'] = gdf_nodes_cn.loc[
        gdf_nodes_cn['CnSide'] == 1, 'endpoint1']
    gdf_nodes_cn.loc[gdf_nodes_cn['CnSide'] == 2, 'geometry'] = gdf_nodes_cn.loc[
        gdf_nodes_cn['CnSide'] == 2, 'endpoint2']

    gdf_bc_lines_hxsx['geom_hxsx'] = gdf_bc_lines_hxsx['geometry']
    gdf_nodes_cn_bc = gdf_nodes_cn.sjoin(gdf_bc_lines_hxsx,
                                         predicate='intersects',
                                         lsuffix='node_bc',
                                         rsuffix='bc').copy(deep=True)
    if len(gdf_nodes_cn_bc) == 0:
        return gdf_nodes_cn_bc

    # print(f'Nodes CN BC: {gdf_nodes_cn_bc}')
    # print(gdf_nodes_cn_bc.apply(
    #     lambda x:
    #     1 if shapely.distance(shapely.get_point(x['polyline'], x['CnSide']),
    #                           shapely.get_point(x['geom_hxsx'], 0)) < 0.01
    #     else 2 if shapely.distance(shapely.get_point(x['polyline'], x['CnSide']),
    #                                shapely.get_point(x['geom_hxsx'], -1)) < 0.01 else -1,
    #     axis=1
    # ))
    gdf_nodes_cn_bc.loc[:, 'hxsx_side'] = gdf_nodes_cn_bc.loc[:, ['polyline', 'geom_hxsx', 'CnSide']].apply(
        lambda x:
        1 if shapely.distance(shapely.get_point(x['polyline'], 0 if x['CnSide'] == 1 else -1),
                              shapely.get_point(x['geom_hxsx'], 0)) < 0.01
        else 2 if shapely.distance(shapely.get_point(x['polyline'], 0 if x['CnSide'] == 1 else -1),
                                   shapely.get_point(x['geom_hxsx'], -1)) < 0.01 else -1,
        axis=1
    ).values

    return gdf_nodes_cn_bc
