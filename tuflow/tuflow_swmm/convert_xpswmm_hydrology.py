from pathlib import Path
import geopandas as gpd
import numpy as np
import pandas as pd
import re
from shapely.validation import make_valid

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def convert_xpswmm_hydrology(gdf_gis_nodes,
                             gdf_gis_subcatchments,
                             gdf_swmm_subcatchments,
                             output_crs,
                             feedback=ScreenProcessingFeedback()):
    max_subcatch_per_node = 5

    gdf_gis_subcatchments = gdf_gis_subcatchments.replace('N/A', np.nan).dropna(subset=['CatchNo'])

    # remove any extra columns
    swmm_cols = list(gdf_swmm_subcatchments.columns[:25])
    # If the geometry column was not in the initial number, switch it for the last column
    if 'geometry' not in swmm_cols:
        swmm_cols[-1] = 'geometry'
    gdf_swmm_subcatchments = gdf_swmm_subcatchments[swmm_cols]

    # Had some bad polygons from XPSWMM
    gdf_gis_subcatchments['geometry'] = gdf_gis_subcatchments.apply(lambda row: make_valid(row.geometry), axis=1)

    gdf_hydro = gdf_gis_subcatchments.merge(gdf_gis_nodes,
                                            how='left',
                                            left_on='AssocNode',
                                            right_on='NodeName',
                                            suffixes=('', '_nodes'))

    gdf_hydro = gdf_hydro.drop(columns=['NodeX', 'NodeY', 'NodeName'])

    prefixes_to_expand = [x[:x.find('[')] for x in gdf_hydro.columns if x.endswith('_1')]

    gdf_hydro['CatchNo'] = gdf_hydro['CatchNo'].astype(int)

    for prefix in prefixes_to_expand:
        for number in range(1, max_subcatch_per_node):
            pattern = re.compile(f'{prefix}.*_{number - 1}')
            if number == 1:  # First one doesn't have a number
                pattern = re.compile(f'{prefix}.*(?<![0-5])$')
            cols_to_copy = [x for x in gdf_hydro.columns if pattern.match(x)]
            if len(cols_to_copy) != 1:
                feedback.reportError(f'Invalid number of columns for prefix {prefix}, subcatchment number {number}.'
                                     f'Invalid columns: {cols_to_copy}', fatalError=True)
            col_to_copy = cols_to_copy[0]
            gdf_hydro.loc[gdf_hydro['CatchNo'] == number, prefix] = gdf_hydro.loc[
                gdf_hydro['CatchNo'] == number, col_to_copy]

    feedback.pushInfo(f'Found hydrology fields: {", ".join(prefixes_to_expand)}')

    final_cols = [
                     'Entity',
                     'CatchName',
                     'CatchNo',
                     'AssocNode',
                     'geometry'
                 ] + prefixes_to_expand
    gdf_hydro.crs = output_crs
    gdf_hydro = gdf_hydro[final_cols]

    # Now combine with and apply to SWMM subcatchments
    gdf_swmm_centerpoints = gdf_swmm_subcatchments.copy(deep=True)
    gdf_swmm_centerpoints['poly_geom'] = gdf_swmm_centerpoints['geometry']
    gdf_swmm_centerpoints['geometry'] = gdf_swmm_centerpoints['geometry'].centroid
    print(gdf_swmm_centerpoints)

    gdf_swmm_and_gis = gdf_swmm_centerpoints.sjoin(
        gdf_hydro,
        how='left',
        predicate='within',
    )
    print(gdf_swmm_and_gis)

    # Remove left prefixes
    gdf_swmm_and_gis = gdf_swmm_and_gis.rename(
        columns=lambda x: x.replace('_left', '')
    )

    # rename right to GIS
    gdf_swmm_and_gis = gdf_swmm_and_gis.rename(
        columns=lambda x: x.replace('_right', '_gis')
    )

    gdf_swmm_and_gis['geometry'] = gdf_swmm_and_gis['poly_geom']
    # gdf_swmm_and_gis = gdf_swmm_and_gis[gdf_swmm_subcatchments.columns]

    # drop unneeded columns
    gdf_swmm_and_gis = gdf_swmm_and_gis.drop(
        columns=[
            'poly_geom',
            'index_gis',
            'Entity',
            'CatchName',
            'AssocNode',
        ]
    )

    return gdf_swmm_and_gis


if __name__ == '__main__':
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 200)

    folder = Path(r'D:\models\TUFLOW\test_models\SWMM\SanAntonio\BMT\TUFLOW\model\swmm')

    nodes_filename = folder / 'exported_nodes_hydrology_002.mif'

    catchments_filename = folder / 'exported_catchments.shp'

    output_filename = folder / 'swmm_gis_hydrology.gpkg'

    output_crs = 'EPSG:2278'

    subcatchments_filename = folder / 'hemi_hydrology_001.gpkg'

    gdf_nodes = gpd.read_file(nodes_filename)
    gdf_gis_subcatchments = gpd.read_file(catchments_filename)
    gdf_swmm_subcatchments = gpd.read_file(str(subcatchments_filename), layer='Hydrology--Subcatchments')

    print(gdf_nodes)
    print(gdf_gis_subcatchments)
    print(gdf_swmm_subcatchments)

    gdf_swmm_out = convert_xpswmm_hydrology(gdf_nodes,
                                            gdf_gis_subcatchments,
                                            gdf_swmm_subcatchments,
                                            output_crs)
    # print(gdf_hydro)
    # gdf_hydro.to_file(output_filename, layer='XPSWMM_Hydrology', crs=output_crs)

    print(gdf_swmm_out)
    gdf_swmm_out.to_file(output_filename, layer='SWMM_Hydrology_updated', crs=output_crs)

