has_fiona = False
try:
    import fiona
    has_fiona = True
except ImportError:
    pass # defaulted to False

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import math
import pandas as pd
from pathlib import Path

from shapely.geometry import LineString

from tuflow.tuflow_swmm.layer_util import read_and_concat_layers
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback


def last_segment_vector_normalized(row):
    coords = row['geometry_y'].coords
    vector = [coords[-1][0] - coords[-2][0], coords[-1][1] - coords[-2][1]]
    length = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1])
    vector_norm = (vector[0] / length, vector[1] / length)

    return vector_norm


def extend_multi_link_outfalls_gdf(
    gdf_all_links,
    gdf_outfalls,
    gdf_junctions,
    gdf_conduits,
    channel_ext_length,
    feedback,
):
    outfall_changes = {}

    gdf_outfalls_conduits = gdf_outfalls.merge(gdf_all_links, 'inner', left_on='Name', right_on='To Node')

    gdf_multi_link_outfalls = gdf_outfalls_conduits[gdf_outfalls_conduits.duplicated(['Name_x'])].drop_duplicates(
        subset=['Name_x']
    )
    if len(gdf_multi_link_outfalls) == 0:
        feedback.pushInfo('No outlets found connected to multiple links.')
        return outfall_changes, gdf_junctions, gdf_outfalls, gdf_conduits

    feedback.pushInfo(f'Found {len(gdf_multi_link_outfalls)} links connected to multiple links.')

    for outfall_name in gdf_multi_link_outfalls['Name_x'].tolist():
        feedback.pushInfo(f'Processing {outfall_name}')
        gdf_outfall_links = gdf_outfalls_conduits[gdf_outfalls_conduits['Name_x'] == outfall_name].copy(deep=True)

        gdf_outfall_links[['DirX', 'DirY']] = gdf_outfall_links.apply(
            last_segment_vector_normalized,
            axis=1,
            result_type='expand',
        )

        direction = gdf_outfall_links[['DirX', 'DirY']].sum(axis=0).values
        length = math.sqrt(direction[0] * direction[0] + direction[1] * direction[1])
        direction = direction / length

        outfall_row = gdf_outfalls['Name'] == outfall_name

        outlet_point = gdf_outfalls[outfall_row]['geometry'].iloc[0].coords[0]
        offset_point = outlet_point + channel_ext_length * direction

        # move outlet point to new location
        gdf_outfalls.loc[outfall_row, 'geometry'] = \
            gdf_outfalls.loc[outfall_row, 'geometry'].translate(
                channel_ext_length * direction[0],
                channel_ext_length * direction[1])

        # Create a junction at the original location using original name (to avoid having to change existing conduits)
        new_name = f'ext_{gdf_outfalls.loc[outfall_row, "Name"].iloc[0]}'
        outfall_changes[outfall_name] = new_name
        gdf_new_junction = gpd.GeoDataFrame(
            {
                'Name': outfall_name,
                'Elev': gdf_outfalls.loc[outfall_row, "Elev"],
                'Ymax': 0.0,
                'Y0': 0.,
                'Ysur':0.,
                'Apond':0.,
            },
            geometry=gpd.points_from_xy([outlet_point[0]],
                                        [outlet_point[1]]),
            crs=gdf_outfalls.crs,
        )
        gdf_junctions = pd.concat([gdf_junctions, gdf_new_junction])

        # change the name of the outfall
        gdf_outfalls.loc[outfall_row, 'Name'] = new_name

        # Need to create new ext_conduit
        new_geom = LineString(
            [outlet_point,
             offset_point]
        )
        gdf_new_conduit = gpd.GeoDataFrame(
            {
                'Name': [f'{new_name}_chan'],
                'From Node': [outfall_name],
                'To Node': [new_name],
                'Length': [channel_ext_length],
                'Roughness': [0.02],
                'InOffset': [0.0],
                'OutOffset': [0.0],
                'xsec_XsecType':['Dummy'],
                'xsec_Geom1': [1.0],
                'xsec_Geom2': [1.0],
                'xsec_Geom3': [0.0],
                'xsec_Geom4': [0.0],
                'xsec_Barrels': [1],
            },
            geometry=[new_geom],
            crs=gdf_junctions.crs,
        )
        gdf_conduits = pd.concat([gdf_conduits, gdf_new_conduit])

    return outfall_changes, gdf_junctions, gdf_outfalls, gdf_conduits

def extend_multi_link_outfalls(input_gpkg,
                               output_gpkg,
                               channel_ext_length,
                               feedback=ScreenProcessingFeedback()):
    if not has_gpd or not has_fiona:
        message = ('This tool requires fiona and geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    feedback.pushInfo("Looking for outlets connected to multiple links")

    # Remove output geopackage if exists
    Path(output_gpkg).unlink(missing_ok=True)

    # Will need to add junctions
    gdf_junctions = gpd.read_file(input_gpkg, layer='Nodes--Junctions')

    gdf_conduits = gpd.read_file(input_gpkg, layer='Links--Conduits')

    # gdf_xsecs = gpd.read_file(input_gpkg, layer='Links--XSections')

    alt_link_layers = [
        'Links--Pumps',
        'Links--Orifices',
        'Links--Weirs',
        'Links--Outlets',
    ]

    gdf_all_links = read_and_concat_layers(input_gpkg, alt_link_layers, [gdf_conduits])

    gdf_outfalls = gpd.read_file(input_gpkg, layer='Nodes--Outfalls')

    outfall_changes, gdf_junctions, gdf_outfalls, gdf_conduits = extend_multi_link_outfalls_gdf(
        gdf_all_links,
        gdf_outfalls,
        gdf_junctions,
        gdf_conduits,
        channel_ext_length,
        feedback,
    )

    modified_layers = [
        'Nodes--Junctions',
        'Nodes--Outfalls',
        'Links--Conduits',
    ]

    all_layers = fiona.listlayers(input_gpkg)

    layers_to_copy = list(set(all_layers) - set(modified_layers))

    for layername in layers_to_copy:
        gdf_layer = gpd.read_file(input_gpkg, layer=layername)
        gdf_layer.to_file(output_gpkg, layer=layername)

    # Need to copy unmodified layers to new file
    feedback.pushInfo(f'Writing modified links to: {output_gpkg}')
    gdf_junctions.to_file(output_gpkg, layer='Nodes--Junctions')
    gdf_outfalls.to_file(output_gpkg, layer='Nodes--Outfalls')
    gdf_conduits.to_file(output_gpkg, layer='Links--Conduits')