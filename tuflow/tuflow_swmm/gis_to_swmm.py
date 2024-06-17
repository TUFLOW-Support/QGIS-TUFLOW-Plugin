"""
This file converts GIS layers into full or partial SWMM input files
It assumes that we are using the naming convention used when we convert SWMM files into a Geo-Package
"""
import os

os.environ['USE_PYGEOS'] = '0'

from pathlib import Path

has_fiona = False
try:
    import fiona

    has_fiona = True
except ImportError:
    pass  # defaulted to False
has_gpd = False
try:
    import geopandas as gpd
    has_gpd = True
except ImportError:
    pass  # defaulted to false
import pandas as pd
from shapely.geometry import Point, MultiPoint

from tuflow.tuflow_swmm import swmm_io

from tuflow.tuflow_swmm.swmm_sections import swmm_section_definitions, primary_node_sections, primary_link_sections, \
    tag_table_type
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback

SNAP_TOLERANCE = 0.05


def find_layer_name(folder,
                    gpkg_filename,
                    section):
    # Look through layers in file ignore anything before --
    layers = fiona.listlayers(folder / gpkg_filename)
    for layer in layers:
        pos_minusminus = layer.find('--')
        stripped_layername = layer if pos_minusminus == -1 else layer[pos_minusminus + 2:]
        if stripped_layername == section:
            return layer
    return None


def load_xsec_columns(folder,
                      gpkg_filename,
                      section_name,
                      feedback=ScreenProcessingFeedback()):
    lyr_name = find_layer_name(folder, gpkg_filename, section_name)
    if lyr_name is None:
        return None

    gdf_section = gpd.read_file(folder / gpkg_filename, layer=lyr_name)
    # feedback.pushInfo(str(gdf_section.columns))
    df_naive = gdf_section.copy(deep=True).drop(columns={'geometry'})

    df_naive = (df_naive[['Name'] + [x for x in df_naive.columns if x.startswith('xsec_')]]).rename(
        columns=lambda x: x.replace('xsec_', '')
    ).rename(
        columns={'Name': 'Link'}
    )
    return df_naive


def create_xsection_table(section,
                          folder,
                          gpkg_filename,
                          feedback=ScreenProcessingFeedback()):
    """
    This function creates a XSection table from the conduit, weir, and orifice tables
    """
    dfs_xsecs = []

    dfs_xsecs.append(load_xsec_columns(folder, gpkg_filename, 'Conduits', feedback))
    dfs_xsecs.append(load_xsec_columns(folder, gpkg_filename, 'Weirs', feedback))
    dfs_xsecs.append(load_xsec_columns(folder, gpkg_filename, 'Orifices', feedback))

    dfs_xsecs = [x for x in dfs_xsecs if x is not None]
    if len(dfs_xsecs) == 0:
        return None

    df_xsecs = pd.concat(dfs_xsecs, axis=0)

    # Add any missing columns (weirs, orifices have fewer columns)
    cols_check = ['Geom3', 'Geom4', 'Barrels', 'Culvert', 'Curve', 'Tsect', 'Street']
    cols_add = [x for x in cols_check if x not in df_xsecs.columns]

    df_xsecs.loc[:, cols_add] = None

    # feedback.pushInfo(str(df_xsecs.columns))

    df_section = section.convert_gpkg_df_to_swmm(df_xsecs, feedback)

    return df_section


def create_loss_table(section, folder, gpkg_filename):
    lyr_name = find_layer_name(folder, gpkg_filename, 'Conduits')
    if lyr_name is None:
        return None

    gdf_section = gpd.read_file(folder / gpkg_filename, layer=lyr_name)
    df_naive = gdf_section.copy(deep=True).drop(columns={'geometry'})

    df_naive = (df_naive[['Name'] + [x for x in df_naive.columns if x.startswith('losses_')]]).rename(
        columns=lambda x: x.replace('losses_', '')
    ).rename(
        columns={'Name': 'Link'}
    )
    # drop rows that are effectively blank
    df_naive = df_naive.dropna(axis=0, how='all', subset=df_naive.columns[1:])
    return df_naive


def gis_to_swmm(gpkg_filename,
                output_filename,
                feedback=ScreenProcessingFeedback()):
    folder = Path(gpkg_filename).parent

    # extract the node geometry from all the node sections
    feedback.pushInfo('Processing Geometry')
    df_coords = None
    dfs_nodes = []
    for ns in primary_node_sections:
        layer_name = find_layer_name(folder, gpkg_filename, ns)
        if layer_name is not None:
            feedback.pushInfo(f'  Node geometry layer: {layer_name}')
            df = gpd.read_file(folder / gpkg_filename, layer=layer_name)
            idcol = df.columns[0]
            df['Name'] = df[idcol]
            df['X-Coord'] = df['geometry'].x
            df['Y-Coord'] = df['geometry'].y
            df = df[['Name', 'X-Coord', 'Y-Coord']]
            dfs_nodes.append(df)
            # print(df)
    if len(dfs_nodes):
        df_coords = pd.concat(dfs_nodes, axis=0)
        # Make sure we don't end up with duplicates
        df_coords = df_coords.drop_duplicates(subset='Name')

    # extract the link geometry from the primary link sections
    df_verts = None
    dfs_verts = []
    for ns in primary_link_sections:
        layer_name = find_layer_name(folder, gpkg_filename, ns)
        if layer_name is not None:
            # print(layer_name)
            df = gpd.read_file(folder / gpkg_filename, layer=layer_name)
            if df.empty:
                continue
            # print(df)
            # df['geometry'] = df.boundary
            # Let's try to remove first and last point here
            # print(df.geometry)
            # print(df.geometry)
            drop_geom = df.geometry.apply(lambda x: len(x.xy[0])) <= 2
            # print(drop_geom)
            df = df[~drop_geom]

            if df.empty:
                # print('Skipping')
                continue

            x_vals = [x for x in list(df.geometry.apply(lambda x: x.xy[0][1:-1].tolist()))]
            y_vals = list(df.geometry.apply(lambda x: x.xy[1][1:-1].tolist()))
            # print(x_vals)
            # print(y_vals)

            multi_pts = []
            for row in zip(x_vals, y_vals):
                # print(row)
                pts = []
                for x, y in zip(row[0], row[1]):
                    # print(x)
                    # print(y)
                    pt = Point(x, y)
                    # print(pt)
                    pts.append(pt)
                multi_pt = MultiPoint(pts)
                # print(multi_pt)
                multi_pts.append(multi_pt)

            df['geometry'] = multi_pts
            df = df.explode(index_parts=False)
            df['X-Coord'] = df.geometry.x
            df['Y-Coord'] = df.geometry.y
            df = df[['Name', 'X-Coord', 'Y-Coord']]
            # print(df)
            dfs_verts.append(df)
    if dfs_verts:
        df_verts = pd.concat(dfs_verts)
        # print(df_verts)

    # Extract the polygons from the subcatchments
    df_poly = None

    lyr_sub = find_layer_name(folder, gpkg_filename, 'Subcatchments')
    if lyr_sub:
        df_poly = gpd.read_file(folder / gpkg_filename, layer=lyr_sub)
        # points2.geometry = points2.geometry.apply(lambda x: MultiPoint(list(x.exterior.coords)))
        try:
            df_poly["geometry"] = df_poly["geometry"].apply(lambda p: MultiPoint(list(p.exterior.coords)))
        except Exception as e:
            empty_geometries = df_poly[df_poly["geometry"].isnull()]['Name'].unique().tolist()
            feedback.reportError(
                f'Unable to process subcatchment polygons. Ensure that the layer is correct and does not contain null geometries. Error: {str(e)}\n'
                f'Emtpy subcatchments: {", ".join(empty_geometries)}',
                fatalError=True)
        df_poly = df_poly.explode(index_parts=False)
        df_poly['X-Coord'] = df_poly.geometry.x
        df_poly['Y-Coord'] = df_poly.geometry.y
        df_poly = df_poly[['Name', 'X-Coord', 'Y-Coord']].drop_duplicates()
        # print(df_poly)

    # for transects, we need both the transects and the coords
    df_transects = None
    df_transects_coords = None

    dfs_tags = []

    # Now that we have generated the geometry sections, go through and write each section that exists to the file
    sections = []
    for section in swmm_section_definitions():
        out_name = section.name

        df_section = None
        if section.name == 'Coordinates':
            df_section = df_coords
        elif section.name == 'Vertices':
            df_section = df_verts
        elif section.name == 'Polygons':
            df_section = df_poly
        else:
            gpkg_layername = section.name
            # Sub-areas are with sub-catchments
            if section.name == 'Subareas':
                gpkg_layername = 'Subcatchments'
            elif section.name == 'Infiltration':
                gpkg_layername = 'Subcatchments'

            lyr_name = find_layer_name(folder, gpkg_filename, gpkg_layername)
            if lyr_name is None and section.name == 'XSections':
                df_section = create_xsection_table(section, folder, gpkg_filename, feedback)
            elif lyr_name is None and section.name == 'Losses':
                df_section = create_loss_table(section, folder, gpkg_filename)
            elif lyr_name is not None:
                gdf_section = gpd.read_file(folder / gpkg_filename, layer=lyr_name)
                df_section = None
                if gdf_section is not None:
                    df_naive = gdf_section.copy(deep=True).drop(columns={'geometry'})
                    # We need to modify the Subarea column names
                    if section.name == 'Subareas':
                        df_naive = df_naive.rename(
                            columns=lambda x: x.replace('Subareas_', '')
                        ).rename(
                            columns={'Name':
                                         'Subcatchment'}
                        )
                    elif section.name == 'Infiltration':
                        df_naive = df_naive.rename(
                            columns=lambda x: x.replace('Infiltration_', '')
                        ).rename(
                            columns={'Name':
                                         'Subcatchment'}
                        )

                    df_section = section.convert_gpkg_df_to_swmm(df_naive)

        if section.name in ['Transects', 'Transects_coords']:
            if section.name == 'Transects':
                df_transects = df_section
            else:
                df_transects_coords = df_section

            if df_transects is not None and df_transects_coords is not None:
                df_transects = df_transects.replace('Nsta', str(len(df_transects_coords)))
                df_section = pd.concat([df_transects, df_transects_coords]).sort_values('Name', kind='stable')
                df_section = df_section.drop(columns=['Name'])
                out_name = 'Transects'
            else:
                df_section = None

        if df_section is not None:
            feedback.pushInfo(f'Processing section: {out_name}')

            # extract tags information if it exists
            if 'Tag' in df_section.columns:
                if section.name in tag_table_type:
                    df_tags = df_section[[df_section.columns[0], 'Tag']].copy(deep=True)
                    df_tags['Object_type'] = tag_table_type[section.name]
                    df_tags = df_tags[['Object_type', df_section.columns[0], 'Tag']]
                    df_tags['Tag'] = df_tags['Tag'].str.strip()
                    df_tags = df_tags[~(df_tags['Tag'].isin(['', 'None', None]))]
                    df_tags = df_tags.dropna(subset=['Tag'])
                    if len(df_tags) > 0:
                        dfs_tags.append(df_tags)

                df_section = df_section.drop(columns='Tag')

            section_text = swmm_io.df_to_swmm_section(df_section,
                                                      out_name,
                                                      out_name == 'Map',
                                                      out_name in ['Curves'])
            sections.append(section_text)

    # Do tags section
    feedback.pushInfo('Gathering tags')
    if len(dfs_tags) > 0:
        df_tags = pd.concat(dfs_tags, axis=0)
        tags_text = swmm_io.df_to_swmm_section(df_tags,
                                               'Tags',
                                               False,
                                               False)
        sections.append(tags_text)

    feedback.pushInfo(f'\n\nWriting to file: {output_filename}')
    # feedback.pushInfo(f'Number of sections: {len(sections)}')
    with open(output_filename, "w") as out_file:
        for isection, section in enumerate(sections):
            # feedback.pushInfo(f'Section {isection}\n')
            # feedback.pushInfo(section + '\n')
            out_file.write(section + '\n')
    feedback.pushInfo('Finished writing file')


def add_polyline_node_names(gdf_polylines, gdf_nodes, first_coords, column_name: str) :
    index = 0 if first_coords else -1
    coords = gdf_polylines["geometry"].apply(lambda g: g.coords[index])
    coords = pd.DataFrame([[x, y] for x, y in coords])

    gdf_end_points = gpd.GeoDataFrame(
        gdf_polylines[['Name']],
        geometry=gpd.points_from_xy(coords[0], coords[1]),
        crs=gdf_polylines.crs,
    )
    gdf_end_points_nodes = gpd.sjoin_nearest(
        gdf_end_points,
        gdf_nodes,
        how='left',
        max_distance=SNAP_TOLERANCE,
    )
    # print(gdf_end_points_nodes)
    # print(gdf_nodes)
    gdf_polylines[column_name] = gdf_end_points_nodes['Name_right']

    return gdf_polylines


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 200)

    files = [
        #Path(
        #    r"D:\models\TUFLOW\test_models\SWMM\SanAntonio\Hemisfair-Cesar Chavez Drainage study\BMT\TUFLOW\model\swmm\Hemisfair_Ult-Mata_Labor_subcatchments.gpkg"
        #)
        Path(
            r"D:\models\TUFLOW\test_models\SWMM\XPSWMM_convert\xpx_file_testing\1D2D_Urban_datechange_001.gpkg"
        )
    ]

    # folder = Path(r"D:\models\TUFLOW\test_models\SWMM\EPA_examples\Samples_conv")
    # pattern = '*.gpkg'
    # files = list(folder.glob(pattern))

    for file in files:
        print(file)
        # gpkg_filename = "Culvert_Model_gpkg.gpkg"
        # output_filename = 'SF_complete_outlets_streets_002.inp'
        output_filename = file.with_stem(file.stem + '_converted').with_suffix('.inp')

        # folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\Ruskin\TUFLOW\SWMM')
        # gpkg_filename = 'Ruskin_005B.gpkg'
        # output_filename = 'Ruskin_005B.inp'

        # This version assumes that they are using standard naming convention
        # layers = {
        #     'Conduits': 'conduits',
        #     'Streets': 'streets',
        #     'Junctions': 'junctions',
        #     # 'Street Nodes': 'street_nodes',
        #     'Inlet Definitions': 'inlets',
        #     'Inlet Usage': 'inlet_usage',
        #     'Xsecs': 'xsections',
        #     # 'Raingages': 'raingages',
        #     # 'Subcatchments': 'subcatchments',
        #     # 'Subareas': 'subareas'
        # }

        # This is for time-series curves from a csv file
        # ts_filename = None
        # ts_headers = None

        # ts_filename = "EG03_005_times10.csv"
        # ts_headers = [
        #    ('Time', 'Rainfall'),
        # ]

        gis_to_swmm(file,
                    output_filename)
        print('\n\n\n')
