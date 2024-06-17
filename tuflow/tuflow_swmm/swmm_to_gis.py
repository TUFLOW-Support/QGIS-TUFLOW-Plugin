import os
import sys

os.environ['USE_PYGEOS'] = '0'
has_gpd = False
gpd = None
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
import datetime
import pandas as pd
from pathlib import Path
from shapely.geometry import LineString, Polygon
from tuflow.tuflow_swmm import swmm_io
from tuflow.tuflow_swmm import swmm_sections
from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf
from tuflow.tuflow_swmm.swmm_sections import swmm_section_definitions
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback

# These sections are redundant because the coordinates are elsewhere
sections_to_not_write = {
    'Losses',
    'XSections',
    'Polygons',
    'Coordinates',
    'Vertices',
    'Subareas',
    'Infiltration',
}

sys.path.append('C:\\Program Files\\git\\cmd\\')


def swmm_to_gpkg(input_filename, output_filename, crs, tags_to_filter=None, feedback=ScreenProcessingFeedback()):
    text_sections = swmm_io.parse_sections(input_filename)

    dfs = {}
    gdfs = {}

    # Filter to the sections in usage
    swmm_section_list = swmm_section_definitions()
    swmm_section_list = [d for d in swmm_section_list if f'[{d.name.upper()}]' in text_sections.keys()]

    added_section_names = set()

    # convert the sections to tables
    dropped_sections = set()

    feedback.pushInfo('\nReading the inp file:')
    for swmm_section in swmm_section_list:
        section_heading = f'[{swmm_section.name.upper()}]'
        feedback.pushInfo(f'Reading: {section_heading}')
        section_text_array = text_sections[section_heading][1]

        try:
            extra_dfs = {}  # dictionary of names and df for extra dataframes created

            df_section = swmm_section.convert_text_to_dataframe(section_text_array, extra_dfs)

            if df_section is None or len(df_section) == 0:
                feedback.pushInfo('  Blank section skipping...')
                dropped_sections.add(swmm_section.name)
            else:
                dfs[swmm_section.name] = df_section

                for name, df in extra_dfs.items():
                    dfs[name] = df
                    # Add the appropriate SWMM section

                if extra_dfs:
                    added_section_names.update([x.upper() for x in extra_dfs.keys()])
        except Exception as e:
            feedback.reportError(str(e))

    added_sections = swmm_section_definitions()
    added_sections = [d for d in added_sections if f'{d.name.upper()}' in added_section_names]
    swmm_section_list.extend(added_sections)
    swmm_section_list = [x for x in swmm_section_list if x.name not in dropped_sections]

    feedback.pushInfo('\n\nProcessing the data...')
    # Create the point geometries
    feedback.pushInfo('Creating coordinates table')
    df_coords = dfs.get('Coordinates', None)
    gdf_coords = None
    if df_coords is not None:
        gdf_coords = gpd.GeoDataFrame(
            df_coords,
            geometry=gpd.points_from_xy(df_coords['X-Coord'], df_coords['Y-Coord'], crs=crs))

    # Get the Link geometries
    gdf_links = None
    df_verts = dfs.get('Vertices', None)
    if df_verts is not None:
        df_links = df_verts.reset_index()
        gdf_links = gpd.GeoDataFrame(
            df_links,
            geometry=gpd.points_from_xy(df_links['X-Coord'], df_links['Y-Coord'], crs=crs))
        gdf_links = gdf_links[['Link', 'index', 'geometry']]
    else:
        # Create a blank Data Fame
        gdf_links = gpd.GeoDataFrame(
            data={'Link': [],
                  'index': [],
                  'geometry': []},
            crs=crs,
        )
        gdf_links = gdf_links[['Link', 'index', 'geometry']]

    # Go through each geometry that is a link type (should have a "To Node" and "From Node" column)
    dfs_exterior_pts = []
    for swmm_section in swmm_section_list:
        if swmm_section.geometry == swmm_sections.GeometryType.LINKS:
            df = dfs[swmm_section.name]
            if df is None:
                continue
            # If there are to and from nodes (XSECTIONS don't have it assume already defined). Add them to geom
            if 'To Node' in df.columns and 'From Node' in df.columns:
                df_coords1 = df.merge(gdf_coords, how='left', left_on='From Node', right_on='Node')
                df_coords1 = df_coords1[['Name', 'geometry']].rename(columns={'Name': 'Link'})
                # want first node to be lowest
                df_coords1['index'] = -1
                # print(df_coords1)
                df_coords1 = df_coords1[['Link', 'index', 'geometry']]
                # print(df_coords1)
                df_coords2 = df.merge(gdf_coords, how='left', left_on='To Node', right_on='Node')
                df_coords2 = df_coords2[['Name', 'geometry']].rename(columns={'Name': 'Link'})
                # want second node to be last
                df_coords2['index'] = 999999
                df_coords2 = df_coords2[['Link', 'index', 'geometry']]
                # print(df_coords2)

                dfs_exterior_pts.append(df_coords1)
                dfs_exterior_pts.append(df_coords2)

    gdf_links = pd.concat([gdf_links] + dfs_exterior_pts, axis=0)
    if len(gdf_links) > 0:
        gdf_links = gdf_links.sort_values(['Link', 'index'])
        try:
            gdf_links = gdf_links.groupby(['Link'])['geometry'].apply(lambda x: LineString(x.tolist()))
            gdf_links = gpd.GeoDataFrame(gdf_links,
                                         geometry='geometry',
                                         crs=crs)
        except:
            feedback.reportError(
                'Some of the Link geometry is invalid.'
                ' Check that all links (conduits, weirs, etc) have valid to and from nodes.')
            gdf_links = None
    else:
        gdf_links = None

    # Get the subcachment polygons
    gdf_polys = None
    df_polys = dfs.get('Polygons', None)
    if df_polys is not None:
        feedback.pushInfo('Converting subcatchment polygon data')
        gdf_polys = gpd.GeoDataFrame(
            df_polys,
            geometry=gpd.points_from_xy(df_polys['X-Coord'], df_polys['Y-Coord'],
                                        crs=crs))
        gdf_polys = gdf_polys.groupby(['Subcatchment'])['geometry'].apply(lambda x: Polygon([(i.x, i.y) for i in x]))
        gdf_polys = gpd.GeoDataFrame(gdf_polys,
                                     geometry='geometry',
                                     crs=crs)

    # Use X-Coord and Y-Coord for tables that are not nodes, links and subcatchments
    for swmm_section in swmm_section_list:
        if swmm_section.section_type == swmm_sections.SectionType.GEOMETRY and \
                swmm_section.geometry == swmm_sections.GeometryType.MISC:
            df = dfs[swmm_section.name]
            gdf = gpd.GeoDataFrame(
                df,
                geometry=gpd.points_from_xy(df['X-Coord'], df['Y-Coord'], crs=crs))
            gdfs[swmm_section.name] = gdf

    # Apply the point geometry tables using geosource = Nodes
    for swmm_section in swmm_section_list:
        if swmm_section.geometry == swmm_sections.GeometryType.NODES and \
                swmm_section.section_type != swmm_sections.SectionType.GEOMETRY:
            try:
                df = dfs[swmm_section.name]
                if df is None:
                    continue
            except:
                continue
            id_col = 'Name' if 'Name' in df.columns else 'Node'
            if gdf_coords is not None:
                gdf = df.merge(gdf_coords[['Node', 'geometry']], how='left', left_on=id_col, right_on='Node')
                if id_col == 'Name':
                    gdf = gdf.drop(columns={'Node'})
                gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
            else:
                # we do not have coordinates, do table without geometry
                gdf = gpd.GeoDataFrame(df, geometry=[None] * len(df))
            gdfs[swmm_section.name] = gdf

    # Apply the geometry tables for inlets (put at inlet node)
    for swmm_section in swmm_section_list:
        if swmm_section.geometry == swmm_sections.GeometryType.INLETS:
            df = dfs[swmm_section.name]
            gdf = df.merge(gdf_coords[['Node', 'geometry']], how='left', left_on='Node', right_on='Node')
            gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
            gdfs[swmm_section.name] = gdf

    # Apply the link geometry to tables using geosource = Links
    feedback.pushInfo("Linking geometry to Link tables")
    for swmm_section in swmm_section_list:
        if swmm_section.geometry == swmm_sections.GeometryType.LINKS:
            if gdf_links is None:
                continue
            df = dfs[swmm_section.name]
            id_col = 'Name' if 'Name' in df.columns else 'Link'
            df[id_col] = df[id_col].astype(str)
            gdf = df.merge(gdf_links, how='left', left_on=id_col, right_index=True)
            gdf = gpd.GeoDataFrame(gdf, geometry='geometry')

            # merge tags if they exist
            # df_tags = dfs.get('TAGS', None)
            # if df_tags is not None:
            #     df_tags = df_tags[df_tags['Object_type'] == 'Link']
            #     gdf = gdf.merge(df_tags, how='left', left_on=id_col, right_on='Object')
            #     gdf = gdf.drop(columns=[
            #         'Object_type',
            #         'Object'
            #     ])
            #     if tags_to_filter:
            #         gdf = gdf[~gdf['Tag'].isin(tags_to_filter)]
            gdfs[swmm_section.name] = gdf

    # Apply the polygon geometry to tables using geosource=Subcatchments
    for swmm_section in swmm_section_list:
        if swmm_section.geometry == swmm_sections.GeometryType.SUBCATCHMENTS and \
                swmm_section.section_type != swmm_sections.SectionType.GEOMETRY:
            df = dfs[swmm_section.name]
            id_col = 'Name' if 'Name' in df.columns else 'Subcatchment'
            gdf = None
            if gdf_polys is None:
                feedback.pushInfo(f'No polygon geometry found for section {swmm_section.name}')
                gdf = gpd.GeoDataFrame(df, geometry=[None] * len(df))
            else:
                gdf = df.merge(gdf_polys, how='left', left_on=id_col, right_index=True)
                gdf = gpd.GeoDataFrame(gdf, geometry='geometry')
            gdfs[swmm_section.name] = gdf

    # Merge the XSections table with the conduit, weir, and orifice tables
    if 'Conduits' in gdfs:
        if 'XSections' in dfs:
            print(dfs['XSections'].columns)
            gdf_conduits2 = gdfs['Conduits'].merge(
                dfs['XSections'].rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdfs['Conduits'] = gdf_conduits2.drop(columns=['xsec_Link'])
        else:
            # Add the cross-section columns
            gdfs['Conduits'].loc[:,
            ['xsec_XsecType',
             'xsec_Geom1',
             'xsec_Geom2',
             'xsec_Geom3',
             'xsec_Geom4',
             'xsec_Barrels',
             'xsec_Culvert',
             'xsec_Curve',
             'xsec_Tsect',
             'xsec_Street']] = None

        if 'Losses' in dfs:
            gdf_conduits2 = gdfs['Conduits'].merge(
                dfs['Losses'].rename(columns=lambda x: f'losses_{x}'),
                how='left',
                left_on='Name',
                right_on='losses_Link',
            )
            gdfs['Conduits'] = gdf_conduits2.drop(columns=['losses_Link'])
        else:
            # add columns
            gdfs['Conduits'].loc[:,
            ['losses_Kentry', 'losses_Kexit', 'losses_Kavg', 'losses_Flap', 'losses_Seepage']] = None

    if 'Weirs' in gdfs:
        if 'XSections' in dfs:
            # Drop the columns we don't need (
            df_weir_xsecs = dfs['XSections'].drop(columns={'Barrels',
                                                           'Culvert',
                                                           'Curve',
                                                           'Tsect',
                                                           'Street'})
            gdf_weirs2 = gdfs['Weirs'].merge(
                df_weir_xsecs.rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdfs['Weirs'] = gdf_weirs2.drop(columns='xsec_Link')
        else:
            # Add the cross-section columns
            gdfs['Weirs'].loc[:,
            ['xsec_XsecType',
             'xsec_Geom1',
             'xsec_Geom2',
             'xsec_Geom3',
             'xsec_Geom4',
             ]] = None

    if 'Orifices' in gdfs:
        if 'XSections' in dfs:
            # Drop the columns we don't need (
            df_orifice_xsecs = dfs['XSections'].drop(columns={'Barrels',
                                                              'Culvert',
                                                              'Curve',
                                                              'Tsect',
                                                              'Street'})
            gdf_orifices2 = gdfs['Orifices'].merge(
                df_orifice_xsecs.rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdfs['Orifices'] = gdf_orifices2.drop(columns='xsec_Link')
        else:
            # Add the cross-section columns
            gdfs['Orifices'].loc[:,
            ['xsec_XsecType',
             'xsec_Geom1',
             'xsec_Geom2',
             'xsec_Geom3',
             'xsec_Geom4',
             ]] = None

    # Merge subcatchment and subarea tables
    if 'Subcatchments' in gdfs:
        gdf_subareas = None
        if 'Subareas' not in gdfs:
            gdf_subareas, _ = create_section_gdf('Subareas', crs)
        else:
            gdf_subareas = gdfs['Subareas']
        subcatch2 = gdfs['Subcatchments'].merge(
            gdf_subareas.drop(columns='geometry').rename(columns=lambda x: f'Subareas_{x}'),
            how='left',
            left_on='Name',
            right_on='Subareas_Subcatchment')
        subcatch2 = subcatch2.drop(columns='Subareas_Subcatchment')
        gdfs['Subcatchments'] = subcatch2
        # Remove the subareas tables
        if 'Subareas' in gdfs:
            del gdfs['Subareas']
            dfs['Subareas'] = None

    # Merge subcatchment and infiltration tables
    if 'Subcatchments' in gdfs:
        gdf_infiltration = None
        if 'Infiltration' not in gdfs:
            gdf_infiltration, _ = create_section_gdf('Infiltration', crs)
        else:
            gdf_infiltration = gdfs['Infiltration']
        subcatch2 = gdfs['Subcatchments'].merge(
            gdf_infiltration.drop(columns='geometry').rename(columns=lambda x: f'Infiltration_{x}'),
            how='left',
            left_on='Name',
            right_on='Infiltration_Subcatchment')
        subcatch2 = subcatch2.drop(columns='Infiltration_Subcatchment')
        gdfs['Subcatchments'] = subcatch2
        # Remove the Infiltration tables
        if 'Infiltration' in gdfs:
            del gdfs['Infiltration']
            dfs['Infiltration'] = None

    # add tags if they exist
    if 'Tags' in dfs:
        df_tags = dfs['Tags']
        # print(df_tags)
        for tag_section, tag_type in swmm_sections.tag_table_type.items():
            df_tags_type = df_tags.loc[df_tags['Object_type'] == tag_type]
            if not df_tags_type.empty:
                # Find the data frame
                df_tag_section = None
                from_gdfs = False
                if tag_section in gdfs:
                    df_tag_section = gdfs[tag_section]
                    from_gdfs = True
                elif tag_section in dfs:
                    df_tag_section = dfs[tag_section]

                # No error it just means that we do not have any objects of this type but may have some in other
                # types using the same tag type (Links--Conduits, Links--Orifices, etc)
                if df_tag_section is None:
                    # raise ValueError(f'No section found for tags: {tag_section}')
                    continue

                df_tag_section = df_tag_section.merge(df_tags_type[['Object', 'Tag']],
                                                      how='left',
                                                      left_on=df_tag_section.columns[0],
                                                      right_on='Object').drop(columns=['Object'])
                if tags_to_filter:
                    df_tag_section = df_tag_section[~df_tag_section['Tag'].isin(tags_to_filter)]

                if from_gdfs:
                    gdfs[tag_section] = df_tag_section
                else:
                    dfs[tag_section] = df_tag_section
        dfs.pop('Tags')
        swmm_section_list = [x for x in swmm_section_list if x.name != 'Tags']
    else:
        # We still want to add tag sections
        df_blank_tags, _ = create_section_gdf('Tags', crs)
        for tag_section, tag_type in swmm_sections.tag_table_type.items():
            # Find the data frame
            df_tag_section = None
            from_gdfs = False
            if tag_section in gdfs:
                df_tag_section = gdfs[tag_section]
                from_gdfs = True
            elif tag_section in dfs:
                df_tag_section = dfs[tag_section]

            if df_tag_section is not None:
                df_tag_section = df_tag_section.merge(df_blank_tags[['Object', 'Tag']],
                                                      how='left',
                                                      left_on=df_tag_section.columns[0],
                                                      right_on='Object').drop(columns=['Object'])
                if from_gdfs:
                    gdfs[tag_section] = df_tag_section
                else:
                    dfs[tag_section] = df_tag_section

    # write curves to csv files
    df_curves = dfs.get('TIMESERIES', None)
    if df_curves is not None:
        # Create a folder
        feedback.pushInfo('Writing TIMESERIES curves to csv files')
        curves_folder = output_filename.parent / f'{output_filename.stem}_curves'
        curves_folder.mkdir(exist_ok=True)
        feedback.pushInfo(f'Creating curves folder: {curves_folder}')

        curve_names = list(set(df_curves['Name'].unique().tolist()) - {'1'})
        for curve_name in curve_names:
            df_curve = df_curves[df_curves['Name'] == curve_name].drop(columns={'Name'})
            date_times = True
            try:
                df_curve['Date_time'] = pd.to_datetime(df_curve['Date'] + ' ' + df_curve['Time'])
                df_curve['Hours'] = (df_curve['Date_time'] - df_curve['Date_time'].iloc[0]).dt.total_seconds() / (
                        60. * 60.)
            except:
                # it must not have been date times
                date_times = False
                df_curve['Hours'] = df_curve['Date'].astype(float)
                df_curve['Value'] = df_curve['Time'].astype(float)
            df_curve['HoursDelta'] = (df_curve['Hours'] - df_curve['Hours'].shift(1)).fillna(0.0)
            df_curve['mm_per_hour'] = df_curve['Value'].astype(float)
            df_curve['mm_per_interval'] = df_curve['mm_per_hour'] * df_curve['HoursDelta']
            if date_times:
                df_curve = df_curve[['Date', 'Time', 'Hours', 'mm_per_hour', 'mm_per_interval']]
            else:
                df_curve = df_curve[['Hours', 'mm_per_hour', 'mm_per_interval']]
            df_curve.to_csv(curves_folder / f'{curve_name}.csv',
                            index=False,
                            float_format='%.5g')

    # Convert dates in the options table to use the yyyy-mm-dd format
    if 'Options' in dfs.keys():
        date_fields = ['START_DATE', 'REPORT_START_DATE', 'END_DATE']
        df_options = dfs['Options']

        for date_field in date_fields:
            try:
                if len(df_options[df_options['Option'] == date_field]) > 0:
                    date_text = df_options.loc[df_options['Option'] == date_field, 'Value'].iloc[0]
                    start_date = datetime.datetime.strptime(date_text, '%m/%d/%Y').date()
                    df_options.loc[df_options['Option'] == date_field, 'Value'] = start_date.isoformat()
            except:
                feedback.reportError(f'Error parsing options field {date_field}: '
                                     f'{df_options.loc[df_options["Option"] == date_field, "Value"]}')

    # write the tables to the geopackage (use gdf if it exists otherwise write dataframe)
    feedback.pushInfo(f'Writing data to Geo-Package: {output_filename}')

    # if it s a new file write a table with the version information
    if not Path(output_filename).exists():
        swmm_io.write_tuflow_version(output_filename)

    # print(swmm_section_list)
    # print(gdfs.keys())
    # print(dfs.keys())
    for i, swmm_section in enumerate(swmm_section_list):
        if swmm_section.name in sections_to_not_write:
            continue

        if swmm_section.prefix != '':
            layer_name = f'{swmm_section.prefix}--{swmm_section.name}'
        else:
            layer_name = swmm_section.name

        if swmm_section.name in gdfs.keys():
            # Make sure description is the last column if it exists
            gdf_section = gdfs[swmm_section.name]
            if 'Description' in gdf_section.columns:
                gdf_section.insert(len(gdf_section.columns) - 1,
                                   'Description',
                                   gdf_section.pop('Description'))
            gdf_section.to_file(output_filename, layer=layer_name, driver='GPKG')
        else:
            df = dfs[swmm_section.name]
            if df is None:
                # don't write tables we are not using
                pass
            else:
                gdf = gpd.GeoDataFrame(dfs[swmm_section.name], geometry=[None for i in df.index])
                if 'Description' in gdf.columns:
                    gdf.insert(len(gdf.columns) - 1, 'Description', gdf.pop('Description'))
                gdf.to_file(output_filename, layer=layer_name, driver='GPKG', index=False)


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 200)

    # input_file = Path(
    #   r"D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\SF\TUFLOW\SWMM\SF_complete_outlets_streets_export.inp")
    # input_file = Path(
    #    r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\Ruskin\TUFLOW\SWMM\Ruskin_002.inp')
    # input_file = Path(
    #       r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\swmm\onechan_trap.inp')
    # files = [
    #    Path(
    #        r"D:\models\TUFLOW\test_models\SWMM\GeoPackage_merge_xsections_losses\All 57 culvert types example.inp"
    #    )
    # ]

    folder = Path(r"D:\models\TUFLOW\test_models\SWMM\q3\GTModel_2024-05-20\BMT\TUFLOW\model\swmm")
    pattern = '*main_mod.inp'

    files = list(folder.glob(pattern))
    files = list(filter(lambda x: str(x).find('_conv.inp') == -1, files))

    for input_file in files:
        # print(input_file)
        output_file = input_file.with_stem(input_file.stem + '_gpkg').with_suffix('.gpkg')
        output_file.unlink(missing_ok=True)

        # Didn't get the right projection
        # projection_filename = Path(r"D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\SF\Projection.prj")
        # with open(projection_filename, 'r') as projection_file:
        #    crs = projection_file.read()
        #    print(crs)

        crs = None

        swmm_to_gpkg(input_file, output_file, crs)
        print('\n\n\n')
