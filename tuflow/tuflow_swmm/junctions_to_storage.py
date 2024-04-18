has_gpd = False
try:
    import geopandas as gpd
    import pandas as pd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def junctions_to_storage(gdf_junctions,
                         gdf_bc_conn,
                         shape_option,
                         length,
                         width,
                         z,
                         feedback=ScreenProcessingFeedback()):
    orig_junction_columns = gdf_junctions.columns

    gdf_bc_conn = gdf_bc_conn.rename(columns={'Type': 'BC_Type'})

    # we only want connections that are HX and not SX connections
    gdf_cn = gdf_bc_conn[gdf_bc_conn['BC_Type'].str.upper().str.contains('CN')]

    gdf_hx = gdf_bc_conn[gdf_bc_conn['BC_Type'].str.upper().str.contains('HX')]

    # CN lines that are connected to HX lines
    gdf_cn_hx = gpd.sjoin_nearest(gdf_cn,
                                  gdf_hx,
                                  how='inner',
                                  max_distance=0.001,
                                  lsuffix='left',
                                  rsuffix='cnhx')
    gdf_cn_hx = gdf_cn_hx.rename(columns=lambda x: x.replace('_left', ''))

    gdf_junctions = gpd.sjoin_nearest(gdf_junctions,
                                      gdf_cn_hx[['geometry', 'BC_Type']],
                                      how='left',
                                      max_distance=0.001,
                                      rsuffix='_bc_conn')
    gdf_junctions = gdf_junctions.drop_duplicates(subset='Name')

    gdf_junctions['has_bc_conn'] = ((gdf_junctions['BC_Type'] is not None) &
                                    (gdf_junctions['BC_Type'].astype(str) != 'None') &
                                    (gdf_junctions['BC_Type'].astype(str) != 'nan') &
                                    (gdf_junctions['BC_Type'].astype(str) != ''))

    print(gdf_junctions)

    gdf_out_junctions = gdf_junctions[~gdf_junctions['has_bc_conn']].copy(deep=True)[orig_junction_columns]

    gdf_out_storage = gdf_junctions[gdf_junctions['has_bc_conn']].copy(deep=True)
    storage_fields = [
        'Name',
        'Elev',
        'Ymax',
        'Y0',
        'TYPE',
        'Acurve',
        'A1',
        'A2',
        'A0',
        'L',
        'W',
        'Z',
        'Ysur',
        'Fevap',
        'Psi',
        'Ksat',
        'IMD',
        'Tag',
        'Description'
    ]
    print(gdf_out_storage.columns)
    print(type(gdf_out_storage.columns))
    new_fields = list(set(storage_fields) - set([str(x) for x in gdf_out_storage.columns.values]))
    gdf_out_storage.loc[:, new_fields] = None
    gdf_out_storage = gdf_out_storage[storage_fields + ['geometry']]

    gdf_out_storage['TYPE'] = shape_option
    gdf_out_storage['L'] = length
    gdf_out_storage['W'] = width
    gdf_out_storage['Z'] = z
    gdf_out_storage['Ymax'] = 100.0

    return gdf_out_junctions, gdf_out_storage


if __name__ == '__main__':
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 300)
    pd.set_option('max_colwidth', 100)

    # Test with Throsby data
    junction_filename = r"D:\models\TUFLOW\test_models\SWMM\Throsby\HWRS_Huxley\model\swmm\swmm_throsby_114.gpkg"
    gdf_throsby_junctions = gpd.read_file(junction_filename, layer='Nodes--Junctions')

    print(gdf_throsby_junctions.crs)

    bc_throsby_conn_filename = r"D:\models\TUFLOW\test_models\SWMM\Throsby\HWRS_Huxley\model\gis\Throsby_102_TBC.gpkg"
    bc_throsby_conn_layername = '2d_bc_swmm_connections_112D_L'
    gdf_throsby_bc_conn = gpd.read_file(bc_throsby_conn_filename, layer=bc_throsby_conn_layername)

    print(gdf_throsby_bc_conn.crs)

    gdf_throsby_out_junctions, gdf_throsby_out_storage = junctions_to_storage(gdf_throsby_junctions,
                                                                              gdf_throsby_bc_conn,
                                                                              'PYRAMIDAL',
                                                                              15.0,
                                                                              5.0,
                                                                              0.5)
    print('\n\nJunctions:')
    print(gdf_throsby_out_junctions)

    print('\n\nStorage:')
    print(gdf_throsby_out_storage)
