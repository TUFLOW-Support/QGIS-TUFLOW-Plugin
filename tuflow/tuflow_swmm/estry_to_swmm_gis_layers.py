"""
This file converts ESTRY GIS layers into SWMM (gpkg) format.
Initial focus will be on pipe network (pipes, nodes, and inlets)
Unlike when migrating a whole project, this conversion works on individual layers and may have incomplete data.
For example, there may be -99999 to get elevations from 2D (warn users) or automatic nodes for channels (generate)
"""
import os

os.environ['USE_PYGEOS'] = '0'

has_gpd = False
gpd = None
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

import numpy as np
import pandas as pd
from pathlib import Path

from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf, create_section_from_gdf
from tuflow.tuflow_swmm.estry_to_swmm import hw_curve_from_xz, create_curves_from_dfs, pit_inlet_dbase_to_df
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.swmm_defaults import default_options_table, default_reporting_table

pd.set_option('display.max_columns', 500)
pd.set_option('display.max_rows', 100)
pd.set_option('display.min_rows', 50)
pd.set_option('display.width', 300)
pd.set_option('max_colwidth', 100)

# TODO
# Handle Irregular culverts


ecf_column_names = {
    'Network':
        [
            'ID',
            'Type',
            'Ignore',
            'UCS',
            'Len_or_ANA',
            'n_or_n_F',
            'US_Invert',
            'DS_Invert',
            'Form_Loss',
            'pBlockage',
            'Inlet_Type',
            'Conn_1D_2D',
            'Conn_No',
            'Width_or_Dia',
            'Height_or_WF',
            'Number_of',
            'Height_Cont',
            'Width_Cont',
            'Entry_Loss',
            'Exit_Loss',
        ],
    'Node':
        [
            'ID',
            'Type',
            'Ignore',
            'Bed_Level',
            'ANA',
            'Conn_1D_2D',
            'Conn_Width',
            'R1',
            'R2',
            'R3',
        ],
    'Cross-section':
        [
            'Source',
            'Type',
        ],

}


def make_columns_match(df, columns):
    # Rename the columns matching the count of those for the data type
    cols_renaming = {
        x: y for x, y in zip(df.columns[:len(columns)], columns)
    }

    df_out = df.rename(columns=cols_renaming)
    # remove remaining columns except for geometry
    cols_to_drop = [x for x in df_out.columns[len(columns):] if x not in [0, 'geometry']]

    df_out = df_out.drop(columns=cols_to_drop)
    return df_out


def split_filename_into_path_and_layer(filename):
    str_filename = str(filename)

    ext_start = str_filename.find('.gpkg')
    if ext_start == -1:
        return str_filename, None

    # we are a geopackage split into portions
    out_filename = str_filename[:ext_start + 5]
    out_layer = str_filename[ext_start + 6:]

    return out_filename, out_layer


def drop_duplicate_points(gdf, tol):
    # Sort by X
    gdf['Delete'] = False

    gdf['x'] = gdf.geometry.x
    gdf = gdf.sort_values('x')

    # Loop through each geometry checking for duplicates afterwards within tol
    for i in range(len(gdf) - 1):
        # skip if already marked for delete
        if gdf['Delete'].iloc[i]:
            continue
        # print(f'{i}   {gdf.index[i]}')
        duplicates = []
        j = i + 1
        # look only at nodes with larger x values and stop once we pass the tolerance
        while j < len(gdf) and gdf.geometry.x.iloc[j] < gdf.geometry.x.iloc[i] + tol:
            if gdf.geometry.iloc[i].distance(gdf.geometry.iloc[j]) < tol:
                duplicates.append(gdf.index[j])
            j = j + 1

        if len(duplicates) > 0:
            duplicates.append(gdf.index[i])
            duplicates.sort()
            # Grab the lowest elevation in case we need it
            lowest_elev = gdf.loc[duplicates, 'Elev'].min()
            gdf.loc[duplicates, 'Elev'] = lowest_elev
            # mark all but the first one to delete
            for dup in duplicates[1:]:
                gdf.loc[dup, 'Delete'] = True
            # print(duplicates)

    gdf = gdf[~gdf['Delete']]
    gdf = gdf.drop(columns=['Delete', 'x'])

    return gdf


def validate_gis_columns(gdf, columns, layer_type, feedback, filename):
    if len(gdf.columns) < len(columns):
        feedback.reportError(f"Not enough columns provided for {layer_type} layer: {filename}", True)
        raise ValueError(f"Not enough columns provided for {layer_type} layer: {filename}")
    gdf = make_columns_match(gdf, columns)
    return gdf


def validate_df(df, column_map, dataframe_name, function_name, feedback):
    missing_cols = set(column_map.keys()) - set(df.columns)
    if len(missing_cols) > 0:
        message = f'Missing columns in processing dataframe {dataframe_name}: {", ".join(sorted(missing_cols))}\n' \
                  f'Dataframe columns: {", ".join(df.columns)}'
        feedback.reportError(message, True)


def create_inlet_usage_table(
        gdf_pits,
        street_name,
        street_slope_pct,
        reference_cell_size,
        crs,
        feedback,
):
    check_pitA_to_inlet_usage_map = {
        'Name': 'Inlet',
        'Number_of': 'Number',
        'pBlockage': 'CloggedPct',
        'Pit_elev': 'Elevation',
        'geometry': 'geometry',
        'Conn_1D_2D': 'Conn1D_2D',
        'Conn_No': 'Conn_width'
    }
    validate_df(gdf_pits,
                check_pitA_to_inlet_usage_map,
                "gdf_pits",
                "create_inlet_usage_table",
                feedback)

    gdf_inlet_usage_ext, inlet_usage_ext_layername = create_section_from_gdf('Inlet_Usage_ext',
                                                                             crs,
                                                                             gdf_pits,
                                                                             check_pitA_to_inlet_usage_map)

    gdf_inlet_usage_ext['Number'] = gdf_inlet_usage_ext['Number'].clip(lower=1)

    gdf_inlet_usage_ext['StreetXSEC'] = street_name
    gdf_inlet_usage_ext['SlopePct_Long'] = street_slope_pct
    gdf_inlet_usage_ext['Qmax'] = 0.0  # No restriction
    gdf_inlet_usage_ext['aLocal'] = 0.0
    gdf_inlet_usage_ext['wLocal'] = 0.0
    gdf_inlet_usage_ext['Placement'] = 'ON_SAG'

    # Connection width is number of cells if negative but must be converted to a width if positive
    gdf_inlet_usage_ext.loc[gdf_inlet_usage_ext['Conn_width'] > 0.0, 'Conn_width'] = gdf_inlet_usage_ext.loc[
                                                                                         gdf_inlet_usage_ext[
                                                                                             'Conn_width'] > 0.0,
                                                                                         'Conn_width'].astype(
        float) * reference_cell_size

    return gdf_inlet_usage_ext, inlet_usage_ext_layername


def convert_layers(network_layers, node_layers, pit_layers, table_link_layers,
                   inlet_dbase,
                   street_name, street_slope_pct, reference_cell_size,
                   create_options_report_tables, report_step, min_surface_area,
                   snap_tolerance,
                   swmm_out_filename, ext_inlet_usage_filename,
                   crs,
                   feedback=ScreenProcessingFeedback(),
                   logger=None):
    if not has_gpd:
        message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                   'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
        feedback.reportError(message)
        return

    gdf_nwk_layers_L = []
    gdf_nwk_layers_P = []
    gdf_node_layers = []
    gdf_pit_layers = []
    gdf_table_link_layers = []

    # Load all layers and sort network layers by data type
    for layer in network_layers:
        filename, layer = split_filename_into_path_and_layer(layer)
        gdf = gpd.read_file(filename, layer=layer)
        gdf = validate_gis_columns(gdf, ecf_column_names['Network'], 'Network', feedback, filename)
        # if len(gdf.columns) < len(ecf_column_names['Network']):
        #     feedback.reportError(f"Not enough columns provided for network layer: {filename}", True)
        #     raise ValueError(f"Not enough columns provided for network layer: {filename}")
        # gdf = make_columns_match(gdf, ecf_column_names['Network'])
        gdf['Source'] = filename
        if gdf.geom_type[0] == 'Point':
            feedback.pushInfo(f'Adding point network layer: {filename}{layer if layer else ""}')
            gdf_nwk_layers_P.append(gdf)
        else:
            feedback.pushInfo(f'Adding channel network layer: {filename}{layer if layer else ""}')
            gdf_nwk_layers_L.append(gdf)

    for layer in node_layers:
        filename, layer = split_filename_into_path_and_layer(layer)
        feedback.pushInfo(f'Adding node layer: {filename}{layer if layer else ""}')
        gdf = gpd.read_file(filename, layer=layer)
        gdf = validate_gis_columns(gdf, ecf_column_names['Node'], 'Node', feedback, filename)
        gdf['Source'] = filename
        gdf_node_layers.append(gdf)

    for layer in pit_layers:
        filename, layer = split_filename_into_path_and_layer(layer)
        feedback.pushInfo(f'Adding pit layer: {filename}{layer if layer else ""}')
        gdf = gpd.read_file(filename, layer=layer)
        gdf['Source'] = filename
        gdf_pit_layers.append(gdf)

    for layer in table_link_layers:
        filename, layer = split_filename_into_path_and_layer(layer)
        feedback.pushInfo(f'Adding Table Link layer: {filename}{layer if layer else ""}')
        gdf = gpd.read_file(filename, layer=layer)
        gdf = validate_gis_columns(gdf, ecf_column_names['Cross-section'], 'Cross-section',
                                   feedback, filename)
        gdf['Refer_filename'] = filename
        # feedback.pushInfo(gdf.crs.to_wkt(pretty=True))
        gdf_table_link_layers.append(gdf)

    gdf_all_nwk_L = None
    if gdf_nwk_layers_L:
        gdf_all_nwk_L = pd.concat(gdf_nwk_layers_L).reset_index()
        feedback.pushInfo(f'Total number of network channels: {len(gdf_all_nwk_L)}')

    gdf_all_nwk_P = None
    if gdf_nwk_layers_P:
        gdf_all_nwk_P = pd.concat(gdf_nwk_layers_P).reset_index()
        feedback.pushInfo(f'Total number of network points: {len(gdf_all_nwk_P)}')

    gdf_all_nodes = None
    if gdf_node_layers:
        gdf_all_nodes = pd.concat(gdf_node_layers).reset_index()
        feedback.pushInfo(f'Total number of network points: {len(gdf_all_nodes)}')

    gdf_all_pits = None
    if gdf_pit_layers:
        gdf_all_pits = pd.concat(gdf_pit_layers).reset_index()
        feedback.pushInfo(f'Total number of pits: {len(gdf_all_pits)}')

    gdf_all_table_links = None
    if gdf_table_link_layers:
        gdf_all_table_links = pd.concat(gdf_table_link_layers).reset_index()
        feedback.pushInfo(f'Total number of table links: {len(gdf_all_table_links)}')

    if gdf_all_nwk_L is None and (gdf_all_nwk_P is not None or gdf_all_nodes is not None):
        message = "No Channels Provided: If nodes are provided, network channels mus be provided."
        feedback.reportError(message, True)
        raise ValueError(message)

    # use geometry length for channels with negative length
    gdf_channel_endpoints = None
    gdf_channel_endpoint_buffered = None
    if gdf_all_nwk_L is not None:
        gdf_all_nwk_L.loc[gdf_all_nwk_L['Len_or_ANA'] < 0.0, 'Len_or_ANA'] = \
            gdf_all_nwk_L.loc[gdf_all_nwk_L['Len_or_ANA'] < 0.0, 'geometry'].length

        # Find nodes snapped to channels and create nodes as needed
        gdf_channel_endpoints = gdf_all_nwk_L.boundary.explode(index_parts=True).reset_index(drop=False)
        gdf_channel_endpoints = gdf_channel_endpoints.rename(columns={'level_0': 'ChanIndex',
                                                                      'level_1': 'NodePos'})
        # print(type(gdf_channel_endpoints))
        gdf_channel_endpoints = gdf_channel_endpoints.merge(gdf_all_nwk_L[['ID', 'US_Invert', 'DS_Invert']],
                                                            left_on='ChanIndex',
                                                            right_index=True,
                                                            how='left').rename(columns={'ID': 'ChanID'})
        # print(gdf_channel_endpoints)
        gdf_channel_endpoints['NodePos'] += 1

        gdf_channel_endpoints['Elev'] = gdf_channel_endpoints.apply(
            lambda x: x['US_Invert'] if x['NodePos'] == 1 else x['DS_Invert'],
            axis=1
        )

        gdf_channel_endpoints2 = drop_duplicate_points(gdf_channel_endpoints, snap_tolerance)
        gdf_channel_endpoints2['PtGeom'] = gdf_channel_endpoints[0]
        gdf_channel_endpoint_buffered = gdf_channel_endpoints2.copy().set_geometry(
            gdf_channel_endpoints.buffer(snap_tolerance))

    # Find channels connected to nwk_P             # \
    gdf_chan_join_nwk_P = None
    if gdf_all_nwk_L is not None and gdf_all_nwk_P is not None:
        gdf_chan_join_nwk_P = gdf_all_nwk_P \
            .sjoin(gdf_channel_endpoint_buffered,
                   how='inner',
                   predicate='within',
                   lsuffix='node',
                   rsuffix='chan')

        # if DS_Invert for the node is -99999 replace with the 'Elev' which is lowest connected channel elevation
        gdf_chan_join_nwk_P['Name'] = gdf_chan_join_nwk_P['ID'].astype(str)
        gdf_chan_join_nwk_P['Invert'] = gdf_chan_join_nwk_P['DS_Invert_node']
        # print(gdf_chan_join_nwk_P)
        gdf_chan_join_nwk_P.loc[gdf_chan_join_nwk_P['Invert'] < -99998., 'Invert'] = \
            gdf_chan_join_nwk_P.loc[gdf_chan_join_nwk_P['Invert'] < -99998., 'Elev']

        # If the node doesn't have a name give one based on the channel
        blank_rows = gdf_chan_join_nwk_P['Name'].isin(['', 'nan', 'None'])
        gdf_chan_join_nwk_P.loc[blank_rows, 'Name'] = \
            gdf_chan_join_nwk_P.loc[blank_rows, 'ChanID'].str.cat(
                gdf_chan_join_nwk_P.loc[blank_rows, 'NodePos'].astype(str),
                sep='.'
            )

        # We want to identify the items that are not represented in gdf_channel_endpoint_buffered
        # Merge and look for nulls
        gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buffered.merge(
            gdf_chan_join_nwk_P[['ChanID', 'NodePos']].add_suffix('_nwk_P'),
            how='left',
            left_on=['ChanID', 'NodePos'],
            right_on=['ChanID_nwk_P', 'NodePos_nwk_P'],
        )
        gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buf2[
            gdf_channel_endpoint_buf2['ChanID_nwk_P'].isnull()
        ].drop(columns=['ChanID_nwk_P', 'NodePos_nwk_P'])
    #        gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buffered[
    #            ~((gdf_channel_endpoint_buffered['ChanID'].isin(gdf_chan_join_nwk_P['ChanID'])) &
    #              (gdf_channel_endpoint_buffered['NodePos'] == gdf_chan_join_nwk_P['NodePos']))
    #        ]
    # print(gdf_channel_endpoint_buf2)
    else:
        gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buffered

    gdf_chan_join_nodes = None
    if gdf_all_nodes is not None:
        gdf_chan_join_nodes = gdf_all_nodes.sjoin(gdf_channel_endpoint_buf2,
                                                  how='inner',
                                                  predicate='within',
                                                  lsuffix='chan',
                                                  rsuffix='node')
        gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buf2[
            ~gdf_channel_endpoint_buf2['ChanID'].isin(gdf_chan_join_nodes['ChanID'])
        ]
        # print(gdf_chan_join_nodes)

        # if DS_Invert for the node is -99999 replace with the 'Elev' which is lowest connected channel elevation
        gdf_chan_join_nodes['Invert'] = gdf_chan_join_nodes['Bed_Level']
        gdf_chan_join_nodes.loc[gdf_chan_join_nodes['Invert'] < -99998., 'Invert'] = \
            gdf_chan_join_nodes.loc[gdf_chan_join_nodes['Invert'] < -99998., 'Elev']
        gdf_chan_join_nodes['Name'] = gdf_chan_join_nodes['ID'].astype(str)

        gdf_chan_join_nodes[0] = gdf_chan_join_nodes['geometry']
        gdf_chan_join_nodes.set_geometry(0)

    # Pits are in a different category to nodes so it is unclear whether automatic nodes should be named using them
    # gdf_chan_join_pits = None
    # if gdf_all_pits is not None:
    #     gdf_chan_join_pits = gdf_channel_endpoint_buf2.sjoin(gdf_all_pits, how='inner', predicate='contains')
    #     gdf_channel_endpoint_buf2 = gdf_channel_endpoint_buf2[
    #         ~gdf_channel_endpoint_buf2['ChanID'].isin(gdf_chan_join_pits['ChanID'])
    #     ]
    #     print(gdf_chan_join_pits)

    # This represents channel endpoints not snapped to a node and must have "automatic" nodes created

    gdf_automatic_nodes = None
    if gdf_channel_endpoint_buf2 is not None and len(gdf_channel_endpoint_buf2) > 0:
        gdf_automatic_nodes = gdf_channel_endpoint_buf2.copy(deep=True)

        gdf_automatic_nodes['Name'] = gdf_automatic_nodes['ChanID'].str.cat(
            gdf_automatic_nodes['NodePos'].astype(str),
            sep='.')
        gdf_automatic_nodes['Invert'] = gdf_automatic_nodes['Elev']
        gdf_automatic_nodes['Type'] = 'Node'
        gdf_automatic_nodes['Conn_1D_2D'] = None
        gdf_automatic_nodes['Conn_Width'] = None

        if gdf_automatic_nodes is not None:
            gdf_automatic_nodes = gdf_automatic_nodes.set_geometry('PtGeom')
            gdf_automatic_nodes[0] = gdf_automatic_nodes['PtGeom']

    if gdf_chan_join_nwk_P is not None:
        gdf_chan_join_nwk_P = gdf_chan_join_nwk_P.set_geometry('PtGeom')
        gdf_chan_join_nwk_P[0] = gdf_chan_join_nwk_P['geometry']

    gdfs_junctions = []
    if gdf_chan_join_nwk_P is not None:
        gdf_chan_join_nwk_P['Pit_elev'] = gdf_chan_join_nwk_P['US_Invert_node']

        gdfs_junctions.append(gdf_chan_join_nwk_P[['Name', 'Invert', 'Type', 'Conn_1D_2D', 'Conn_No',
                                                   'Number_of', 'pBlockage', 'Pit_elev', 0,
                                                   'Width_or_Dia', 'Height_or_WF', ]])
    if gdf_chan_join_nodes is not None:
        gdf_chan_join_nodes['Number_of'] = 1
        gdf_chan_join_nodes['pBlockage'] = 0.0
        gdf_chan_join_nodes['Pit_elev'] = gdf_chan_join_nodes['Invert']
        gdf_chan_join_nodes['Width_or_Dia'] = 0.0
        gdf_chan_join_nodes['Height_or_WF'] = 0.0
        try:
            gdfs_junctions.append(gdf_chan_join_nodes[['Name', 'Invert', 'Type', 'Conn_1D_2D',
                                                       'Conn_Width', 'Number_of', 'Pit_elev', 0,
                                                       'Width_or_Dia', 'Height_or_WF', ]])
        except Exception:
            feedback.reportError('Error appending junction data. Make sure that input files are correct.'
                                 'ERROR: str(e)')
            return

    if gdf_automatic_nodes is not None:
        gdf_automatic_nodes['Number_of'] = 1
        gdf_automatic_nodes['pBlockage'] = 0.0
        gdf_automatic_nodes['Pit_elev'] = gdf_automatic_nodes['Invert']
        gdfs_junctions.append(gdf_automatic_nodes[['Name', 'Invert', 'Type', 'Conn_1D_2D', 'Conn_Width',
                                                   'Number_of', 'Pit_elev', 0]])

    gdf_junction_data = None
    gdf_junctions = None
    junctions_layername = None
    if gdfs_junctions:
        gdf_junction_data = pd.concat(
            gdfs_junctions,
            axis=0
        )
    if gdf_junction_data is not None:
        gdf_junction_data = gdf_junction_data.rename(columns={0: 'geometry'}).set_geometry('geometry')

        nwk_to_junction_cols = {
            'Name': 'Name',
            'Invert': 'Elev',
            'geometry': 'geometry',
        }

        gdf_junctions, junctions_layername = create_section_from_gdf('Junctions',
                                                                     crs,
                                                                     gdf_junction_data,
                                                                     nwk_to_junction_cols)
        gdf_junctions = drop_duplicate_points(gdf_junctions, 0.00001)

    # Channel nodes - re-export channel endpoints and join to final junctions to get final nodes
    gdf_channel_endpoint_buf_all = None
    if gdf_channel_endpoints is not None:
        gdf_channel_endpoint_buf_all = gdf_channel_endpoints.copy().set_geometry(
            gdf_channel_endpoints.buffer(snap_tolerance))

    # Find channels connected to gdf_junction_data             # \
    gdf_chan_join_junct_data = None
    if gdf_junction_data is not None:
        gdf_chan_join_junct_data = gdf_junction_data \
            .sjoin(gdf_channel_endpoint_buf_all,
                   how='right',
                   predicate='within',
                   lsuffix='chan',
                   rsuffix='node')

        # remove duplicates
        gdf_chan_join_junct_data = gdf_chan_join_junct_data.drop_duplicates(
            subset=['ChanID', 'NodePos']
        )

    gdf_conduits = None
    conduits_layername = None
    if gdf_all_nwk_L is not None:
        # We need ChanIndex/NodePos to inform the channels upstream and downstream nodes also copy elev in case chan is null
        gdf_all_nwk_L = gdf_all_nwk_L.merge(
            gdf_chan_join_junct_data[gdf_chan_join_junct_data['NodePos'] == 1].add_suffix('_node_up'),
            how='left',
            left_on='ID',
            right_on='ChanID_node_up')

        gdf_all_nwk_L = gdf_all_nwk_L.merge(
            gdf_chan_join_junct_data[gdf_chan_join_junct_data['NodePos'] == 2].add_suffix('_node_down'),
            how='left',
            left_on='ID',
            right_on='ChanID_node_down')

        # Initialize In and Out offsets to 0.0
        gdf_all_nwk_L['In Offset'] = 0.0
        gdf_all_nwk_L['Out Offset'] = 0.0

        gdf_all_nwk_L['From Node'] = gdf_all_nwk_L['Name_node_up']
        gdf_all_nwk_L['To Node'] = gdf_all_nwk_L['Name_node_down']
        gdf_all_nwk_L = gdf_all_nwk_L.rename(
            columns=
            {
                'Len_or_ANA': 'Length',
                'n_or_n_F': 'Roughness',
            }
        )
        gdf_all_nwk_L.loc[
            gdf_all_nwk_L['Length'] < -9998., 'Length'
        ] = gdf_all_nwk_L.loc[
            gdf_all_nwk_L['Length'] < -9998., 'geometry'
        ].length
        gdf_all_nwk_L.loc[
            gdf_all_nwk_L['US_Invert'] > -9998, 'In Offset'
        ] = gdf_all_nwk_L.loc[
                gdf_all_nwk_L['US_Invert'] > -9998, 'US_Invert'
            ] - gdf_all_nwk_L.loc[
                gdf_all_nwk_L['US_Invert'] > -9998, 'Invert_node_up'
            ]
        gdf_all_nwk_L.loc[
            gdf_all_nwk_L['DS_Invert'] > -9998, 'Out Offset'
        ] = gdf_all_nwk_L.loc[
                gdf_all_nwk_L['DS_Invert'] > -9998, 'DS_Invert'
            ] - gdf_all_nwk_L.loc[
                gdf_all_nwk_L['DS_Invert'] > -9998, 'Invert_node_down'
            ]

        # For pipes only use types C, I, R, Weirs (W,WB,WC,WD,WO,WR,WT,WV,WW), M, Q
        # We may end up with some open channel segments but the user will need to clean that up
        pipe_channel_types = [
            'C',
            'R',
            'I',
        ]
        # Remove flags and store information elsewhere

        gdf_all_nwk_L['Unidirectional'] = gdf_all_nwk_L['Type'].str.contains('U')
        gdf_all_nwk_L['Type_mod'] = gdf_all_nwk_L['Type'].str.replace('U', '')

        gdf_all_nwk_L['Weir_over_top'] = gdf_all_nwk_L['Type_mod'].isin(['CW', 'RW'])
        gdf_all_nwk_L.loc[
            gdf_all_nwk_L['Weir_over_top'],
            'Type_mod'
        ].str.replace('W', '')

        gdf_all_nwk_L['Operational'] = gdf_all_nwk_L['Type_mod'].str.contains('O')
        gdf_all_nwk_L['Type_mod'] = gdf_all_nwk_L['Type_mod'].str.replace('O', '')

        gdf_nwk_pipes = gdf_all_nwk_L.copy(deep=True)
        gdf_nwk_pipes = gdf_nwk_pipes[gdf_nwk_pipes['Type_mod'].isin(pipe_channel_types)]

        nwkc_to_conduits_map = \
            {
                'ID': 'Name',
                'From Node': 'From Node',
                'To Node': 'To Node',
                'Length': 'Length',
                'Roughness': 'Roughness',
                'In Offset': 'InOffset',
                'Out Offset': 'OutOffset',
                'geometry': 'geometry',
            }
        gdf_conduits, conduits_layername = create_section_from_gdf('Conduits',
                                                                   crs,
                                                                   gdf_nwk_pipes,
                                                                   nwkc_to_conduits_map)

        feedback.pushInfo(f'Number of pipe conduits: {len(gdf_conduits)}')

    # Find channels that overlap cross-sections
    gdf_all_table_links_nwk_ID = None
    if gdf_all_table_links is not None:
        # print(gdf_all_nwk_L.columns)
        gdf_all_table_links_nwk_ID = gdf_all_table_links.sjoin(
            gdf_all_nwk_L[['ID', 'geometry']],
            how='left',
            predicate='intersects',
            lsuffix='',
            rsuffix='nwk'
        )
        gdf_all_table_links_nwk_ID = gdf_all_table_links_nwk_ID[~gdf_all_table_links_nwk_ID['ID'].isnull()]
    #        print(gdf_all_table_links_nwk_ID)

    # Handle bridges (new style) as irregular culverts
    gdf_bridges_bb = None
    bridges_bb_layername = None
    gdf_bridges_bb_curves = None
    gdf_bridges_bb_xsecs = None
    if gdf_all_nwk_L is not None:
        gdf_bridges_bb = gdf_all_nwk_L.copy(deep=True)
        # print(gdf_nwk_pumps['Type_mod'].unique())
        gdf_bridges_bb = gdf_bridges_bb[gdf_bridges_bb['Type_mod'] == 'BB']
        feedback.pushInfo(f'Number of bridges (BB): {len(gdf_bridges_bb)}')

        if len(gdf_bridges_bb) > 0:

            nwkc_to_conduits_map = \
                {
                    'ID': 'Name',
                    'From Node': 'From Node',
                    'To Node': 'To Node',
                    'Length': 'Length',
                    'Roughness': 'Roughness',
                    'In Offset': 'InOffset',
                    'Out Offset': 'OutOffset',
                    'geometry': 'geometry',
                }
            gdf_bridges_bb, bridges_bb_layername = create_section_from_gdf('Conduits',
                                                                           crs,
                                                                           gdf_bridges_bb,
                                                                           nwkc_to_conduits_map)

            gdf_bridges_bb_w_xsec = gdf_bridges_bb.merge(
                gdf_all_table_links_nwk_ID,
                left_on='Name',
                right_on='ID',
                how='left'
            )

            # Bridges will be represented as a custom culvert (HW)
            gdf_bridges_bb_w_xsec['XsecType'] = 'CUSTOM'
            gdf_bridges_bb_w_xsec['Curve'] = gdf_bridges_bb_w_xsec['ID'] + '_hw'

            # Make the HW curves
            dfs = []
            heights = []
            for row in gdf_bridges_bb_w_xsec[['Curve', 'Refer_filename', 'Source', 'Type']].itertuples():
                resolved_filename = Path(row.Refer_filename).parent / row.Source
                zmin, zmax, df = hw_curve_from_xz(resolved_filename)
                dfs.append(df)
                heights.append(zmax - zmin)

            gdf_bridges_bb_curves = create_curves_from_dfs(
                'SHAPE',
                gdf_bridges_bb_w_xsec['Curve'].to_list(),
                dfs,
                crs
            )

            gdf_bridges_bb_w_xsec['Geom1'] = heights

            gdf_bridges_bb_w_xsec['Geom3'] = 0.0
            gdf_bridges_bb_w_xsec['Geom4'] = 0.0
            gdf_bridges_bb_w_xsec['Number_of'] = 1

            nwk_c_to_xsecs_map = {
                'Name': 'Link',
                'XsecType': 'XsecType',
                'Geom1': 'Geom1',
                'Curve': 'Curve',
                'Geom3': 'Geom3',
                'Geom4': 'Geom4',
                'Number_of': 'Barrels',
                'geometry_x': 'geometry',
            }
            gdf_bridges_bb_xsecs, bridges_bb_xsecs_layername = create_section_from_gdf('XSections',
                                                                                       crs,
                                                                                       gdf_bridges_bb_w_xsec,
                                                                                       nwk_c_to_xsecs_map)
            # Merge the bridges into the conduits table
            gdf_conduits = pd.concat((gdf_conduits, gdf_bridges_bb), axis=0)

            # gdf_xsecs['XsecType'] = gdf_pipes_geom['Type_mod'].map(lambda x: 'CIRCULAR' if x.startswith('C')
            # else 'RECT_CLOSED' if x.startswith('R') else 'CUSTOM')

            # gdf_xsecs = gdf_xsecs[gdf_xsecs['Link'].isin(gdf_conduits['Name'])]

            # gdf_pipes_geom['Flap Gate'] = 'No'
            # gdf_pipes_geom.loc[gdf_pipes_geom['Unidirectional'], 'Flap Gate'] = 'Yes'

    # Handle pumps
    gdf_pumps = None
    pumps_layername = None
    if gdf_all_nwk_L is not None:
        gdf_nwk_pumps = gdf_all_nwk_L.copy(deep=True)
        # print(gdf_nwk_pumps['Type_mod'].unique())
        gdf_nwk_pumps = gdf_nwk_pumps[gdf_nwk_pumps['Type_mod'] == 'P']
        feedback.pushInfo(f'Number of pumps: {len(gdf_nwk_pumps)}')

        if len(gdf_nwk_pumps) > 0:
            feedback.pushWarning('WARNING - Only some pump information is transferred when converting ESTRY to SWMM.'
                                 '   Pump curves and on/off elevations must be provided. Verify all pump inputs.')

            # print(gdf_nwk_pumps)

            gdf_nwk_pumps['PumpCurve'] = 'add_pump_curve'
            gdf_nwk_pumps['Status'] = 'OFF'
            nwkc_to_pumps_map = \
                {
                    'ID': 'Name',
                    'Name_node_up': 'From Node',
                    'Name_node_down': 'To Node',
                    'PumpCurve': 'Pcurve',
                    'Status': 'Status',
                    'geometry': 'geometry',
                }
            gdf_pumps, pumps_layername = create_section_from_gdf('Pumps',
                                                                 crs,
                                                                 gdf_nwk_pumps,
                                                                 nwkc_to_pumps_map)

    gdf_weirs = None
    gdf_weir_xsecs = None
    weirs_layername = None

    if gdf_all_nwk_L is not None:
        gdf_nwk_weirs = gdf_all_nwk_L.copy(deep=True)
        gdf_nwk_weirs = gdf_nwk_weirs[gdf_nwk_weirs['Type_mod'].str.startswith('W')]
        feedback.pushInfo(f'Number of weirs: {len(gdf_nwk_weirs)}')

        if len(gdf_nwk_weirs) > 0:
            feedback.pushWarning(
                'WARNING - Weirs converted from ESTRY to SWMM may not be complete or optimal representation.'
                ' Verify and modify the converted weirs as needed.')

            # Default to transverse weir if not supported
            weir_type_mapping = {
                'W': 'TRANSVERSE',
                'WB': 'TRANSVERSE',
                'WC': 'TRANSVERSE',
                'WD': 'TRANSVERSE',
                'WR': 'TRANSVERSE',
                'WT': 'TRAPEZOIDAL',
                'WV': 'V-NOTCH',
                'WW': 'TRANSVERSE',
            }
            weir_coeff_mapping = {
                'W': 0.57,
                'WB': 0.577,
                'WC': 0.508,
                'WD': 0.577,  # TUFLOW User defined
                'WR': 0.62,
                'WT': 0.63,
                'WV': 0.577,  # TUFLOW recalculated
                'WW': 0.542,
            }

            gdf_junctions_indexed = gdf_junctions.set_index('Name')

            # print(gdf_nwk_weirs)
            gdf_nwk_weirs['CrestHt'] = gdf_nwk_weirs[['US_Invert', 'DS_Invert']].max(axis=1) - \
                                       gdf_junctions_indexed.loc[gdf_nwk_weirs['Name_node_up'], 'Elev'].values
            gdf_nwk_weirs['WeirType'] = gdf_nwk_weirs['Type_mod'].apply(lambda x: weir_type_mapping[x])
            gdf_nwk_weirs['Cd'] = gdf_nwk_weirs['Type_mod'].apply(lambda x: weir_coeff_mapping[x])
            gdf_nwk_weirs['Gated'] = gdf_nwk_weirs['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
            # overwrite if not 0
            gdf_nwk_weirs.loc[
                gdf_nwk_weirs['Height_Cont'] > 0.0, 'Cd'
            ] = gdf_nwk_weirs.loc[
                gdf_nwk_weirs['Height_Cont'] > 0.0, 'Height_Cont']
            # Handle multipliers
            gdf_nwk_weirs.loc[
                gdf_nwk_weirs['Height_or_WF'] > 0.0, 'Cd'
            ] *= gdf_nwk_weirs.loc[
                gdf_nwk_weirs['Height_or_WF'] > 0.0, 'Height_or_WF']

            nwkc_to_weirs_map = \
                {
                    'ID': 'Name',
                    'Name_node_up': 'From Node',
                    'Name_node_down': 'To Node',
                    'WeirType': 'Type',
                    'CrestHt': 'CrestHt',
                    'Cd': 'Cd',
                    'Gated': 'Gated',
                    'geometry': 'geometry',
                }
            gdf_weirs, weirs_layername = create_section_from_gdf('Weirs',
                                                                 crs,
                                                                 gdf_nwk_weirs,
                                                                 nwkc_to_weirs_map)

            # Do the xsection shapes
            # print(gdf_nwk_weirs)
            gdf_nwk_weirs = gdf_nwk_weirs[gdf_nwk_weirs['Type_mod'].str.startswith('W')]
            weir_type_to_shape = {
                'TRANSVERSE': 'RECT_OPEN',
                'TRAPEZOIDAL': 'TRAPEZOIDAL',
                'V-NOTCH': 'TRIANGULAR',
                'SIDEFLOW': 'RECT_OPEN',
                'ROADWAY': 'RECT_OPEN',
            }
            gdf_nwk_weirs['WeirShape'] = gdf_nwk_weirs['WeirType'].apply(lambda x: weir_type_to_shape[x])
            gdf_nwk_weirs['WeirGeom1'] = 20.0
            gdf_nwk_weirs['WeirGeom2'] = gdf_nwk_weirs['Width_or_Dia']
            gdf_nwk_weirs['WeirBarrels'] = 1

            # print(gdf_nwk_weirs)
            gdf_nwk_weirs.loc[
                gdf_nwk_weirs['WeirGeom2'] == 0.0, 'WeirGeom2'] = gdf_nwk_weirs.loc[
                gdf_nwk_weirs['WeirGeom2'] == 0.0, 'Width_or_Dia']
            gdf_nwk_weirs.loc[:, ['WeirGeom3', 'WeirGeom4']] = 0.0
            gdf_nwk_weirs.loc[
                gdf_nwk_weirs['WeirType'] == 'TRAPEZOIDAL', ['WeirGeom3', 'WeirGeom4']] = 1.0

            nwkc_to_weir_xsecs_map = {
                'ID': 'Link',
                'WeirShape': 'XsecType',
                'WeirGeom1': 'Geom1',
                'WeirGeom2': 'Geom2',
                'WeirGeom3': 'Geom3',
                'WeirGeom4': 'Geom4',
                'WeirBarrels': 'Barrels',
                'geometry': 'geometry'
            }
            gdf_weir_xsecs, _ = create_section_from_gdf('XSections',
                                                        crs,
                                                        gdf_nwk_weirs,
                                                        nwkc_to_weir_xsecs_map)

    # Handle Sluice Gates (become orifices)
    gdf_orifices = None
    gdf_sg_xsecs = None
    orifices_layername = None
    gdf_nwk_sg = None
    if gdf_all_nwk_L is not None:
        gdf_nwk_sg = gdf_all_nwk_L.copy(deep=True)
        gdf_nwk_sg = gdf_nwk_sg[gdf_nwk_sg['Type_mod'].str.startswith('SG')]

        if len(gdf_nwk_sg) > 0:
            feedback.pushInfo(f'Number of weirs: {len(gdf_nwk_sg)}')

            # print(gdf_nwk_sg)
            gdf_nwk_sg['SgType'] = 'SIDE'
            gdf_nwk_sg['Gated'] = gdf_nwk_sg['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
            gdf_nwk_sg['Offset'] = 0.0
            nwkc_sg_to_orifices_map = \
                {
                    'ID': 'Name',
                    'Name_node_up': 'From Node',
                    'Name_node_down': 'To Node',
                    'SgType': 'Type',
                    'Offset': 'Offset',
                    'Roughness': 'Qcoeff',
                    'Gated': 'Gated',
                    'geometry': 'geometry',
                }
            gdf_orifices, orifices_layername = create_section_from_gdf('Orifices',
                                                                       crs,
                                                                       gdf_nwk_sg,
                                                                       nwkc_sg_to_orifices_map)

            gdf_nwk_sg_xsecs = gdf_all_nwk_L.copy(deep=True)
            gdf_nwk_sg_xsecs = gdf_nwk_sg_xsecs[gdf_nwk_sg_xsecs['Type_mod'].str.startswith('SG')]
            if len(gdf_nwk_sg_xsecs) > 0:
                gdf_nwk_sg_xsecs['Shape'] = 'RECT_CLOSED'
                gdf_nwk_sg_xsecs['Geom3'] = 0
                gdf_nwk_sg_xsecs['Geom4'] = 0
                gdf_nwk_sg_xsecs['Barrels'] = 1
                nwkc_sg_to_orifices_xsecs_map = {
                    'ID': 'Link',
                    'Shape': 'XsecType',
                    'Height_or_WF': 'Geom1',
                    'Width_or_Dia': 'Geom2',
                    'Geom3': 'Geom3',
                    'Geom4': 'Geom4',
                    'Barrels': 'Barrels',
                    'geometry': 'geometry'
                }
                gdf_sg_xsecs, _ = create_section_from_gdf('XSections',
                                                          crs,
                                                          gdf_nwk_sg_xsecs,
                                                          nwkc_sg_to_orifices_xsecs_map)

    # Handle Q Channels (become outlets)
    gdf_outlets = None
    outlets_layername = None
    if gdf_all_nwk_L is not None:
        gdf_nwk_q = gdf_all_nwk_L.copy(deep=True)
        gdf_nwk_q = gdf_nwk_q[gdf_nwk_q['Type_mod'].str.startswith('Q')]
        feedback.pushInfo(f'Number of Q inlets: {len(gdf_nwk_q)}')
        if len(gdf_nwk_q) > 0:
            feedback.pushWarning('WARNING - Q Channel curves are not copied from ESTRY and need to be created manually')

            gdf_nwk_q['OutletType'] = 'TABULAR/DEPTH'
            gdf_nwk_q['Gated'] = gdf_nwk_sg['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
            gdf_nwk_q['Offset'] = 0.0
            nwkc_q_to_outlets_map = \
                {
                    'ID': 'Name',
                    'Name_node_up': 'From Node',
                    'Name_node_down': 'To Node',
                    'Offset': 'Offset',
                    'OutletType': 'Type',
                    'Inlet_Type': 'QCurve',
                    'Gated': 'Gated',
                    'geometry': 'geometry',
                }
            gdf_outlets, outlets_layername = create_section_from_gdf('Outlets',
                                                                     crs,
                                                                     gdf_nwk_q,
                                                                     nwkc_q_to_outlets_map)

    # Handle pipe cross-sections
    gdf_xsecs = None
    xsecs_layername = None
    gdf_losses = None
    losses_layername = None
    if gdf_all_nwk_L is not None:
        gdf_all_nwk_L['Geom1'] = gdf_all_nwk_L['Width_or_Dia']
        gdf_all_nwk_L.loc[gdf_all_nwk_L['Type_mod'] == 'R', 'Geom1'] = gdf_all_nwk_L.loc[
            gdf_all_nwk_L['Type_mod'] == 'R', 'Height_or_WF']
        gdf_all_nwk_L['Geom2'] = gdf_all_nwk_L['Width_or_Dia']

        gdf_pipes_geom = gdf_all_nwk_L.copy(deep=True)
        # Remove bridges (handled separately)
        gdf_pipes_geom = gdf_pipes_geom[~(gdf_pipes_geom['Type_mod'].str.contains('B') |
                                          gdf_pipes_geom['Type_mod'].str.contains('b'))]
        gdf_pipes_geom['Geom3'] = 0
        gdf_pipes_geom['Geom4'] = 0

        nwk_c_to_xsecs_map = {
            'ID': 'Link',
            'Geom1': 'Geom1',
            'Geom2': 'Geom2',
            'Geom3': 'Geom3',
            'Geom4': 'Geom4',
            'Number_of': 'Barrels',
            'geometry': 'geometry',
        }
        gdf_xsecs, xsecs_layername = create_section_from_gdf('XSections',
                                                             crs,
                                                             gdf_pipes_geom,
                                                             nwk_c_to_xsecs_map)

        gdf_xsecs['XsecType'] = gdf_pipes_geom['Type_mod'].map(lambda x: 'CIRCULAR' if x.startswith('C')
        else 'RECT_CLOSED' if x.startswith('R') else 'CUSTOM')

        gdf_xsecs = gdf_xsecs[gdf_xsecs['Link'].isin(gdf_conduits['Name'])]

        gdf_pipes_geom['Flap Gate'] = 'No'
        gdf_pipes_geom.loc[gdf_pipes_geom['Unidirectional'], 'Flap Gate'] = 'Yes'
        nwk_c_to_losses_map = {
            'ID': 'Link',
            'Entry_Loss': 'Kentry',
            'Exit_Loss': 'Kexit',
            'Form_Loss': 'Kavg',
            'Flap Gate': 'Flap',
            'geometry': 'geometry',
        }
        gdf_losses, losses_layername = create_section_from_gdf('Losses',
                                                               crs,
                                                               gdf_pipes_geom,
                                                               nwk_c_to_losses_map)

        gdf_losses = gdf_losses[gdf_losses['Link'].isin(gdf_conduits['Name'])]

        # print(gdf_losses)
        # drop losses if all losses are 0 and there is no flap gate
        gdf_losses = gdf_losses[
            (gdf_losses['Kentry'] > 0.0) |
            (gdf_losses['Kexit'] > 0.0) |
            (gdf_losses['Kavg'] > 0.0) |
            (gdf_losses['Flap'] == 'Yes')
            ]
        # print(gdf_losses)
        if len(gdf_losses):
            feedback.pushWarning(
                'WARNING - ESTRY pipe losses are adjusted based upon downstream velocities which is not'
                ' supported by SWMM. Verify that the losses copied are appropriate and modify as needed.')

    # TODO - Handle Irregular culverts
    gdf_irr_culv_curves = None
    if gdf_xsecs is not None:
        if len(gdf_xsecs[gdf_xsecs['XsecType'] == 'CUSTOM']) > 0:
            gdf_xsecs['Curve'] = gdf_xsecs['Curve'].astype(str)
            gdf_xsecs.loc[gdf_xsecs['XsecType'] == 'CUSTOM', 'Curve'] = '0'
            feedback.pushWarning("WARNING - Irregular culverts encountered which are not yet converted."
                                 " The SWMM Shape tables must be created and added to the CURVES section of the SWMM input file.")
        #     custom_xsecs = gdf_xsecs['XsecType'] == 'CUSTOM'
        #     gdf_irr_culv_xsec = gdf_xsecs[custom_xsecs]
        #
        #     irr_curve_names, max_heights, gdf_irr_culv_curves = create_hw_curves2(gdf_irr_culv_xsec, filename_ta_check,
        #                                                                           crs, feedback)
        #
        #     gdf_xsecs.loc[custom_xsecs, 'Geom1'] = max_heights
        #     gdf_xsecs.loc[custom_xsecs, 'Curve'] = irr_curve_names
        #     gdf_xsecs.loc[custom_xsecs, 'Dummy'] = 0.0

        gdf_xsecs.set_crs(crs, allow_override=True)

    # Do inlets
    inlets_layername = None
    gdf_inlets_q = None
    gdf_inlets_w = None
    gdf_inlets_r = None
    gdf_inlets_c = None
    gdf_inlets_blank = None

    gdf_outfalls = None
    outfalls_layername = None
    if gdf_all_nwk_L is not None:
        # Identify outfall nodes (nodes that are used as downstream nodes but not upstream nodes)
        all_from_nodes = gdf_all_nwk_L['From Node'].unique()
        gdf_all_nodes = gdf_junctions.copy(deep=True)
        gdf_junctions = gdf_junctions[
            (gdf_junctions['Name'].isin(all_from_nodes))
        ]

        # outfalls
        all_to_nodes = gdf_all_nwk_L['To Node'].unique()
        gdf_junctions_outfalls = \
            gdf_all_nodes[
                (gdf_all_nodes['Name'].isin(all_to_nodes)) &
                (~gdf_all_nodes['Name'].isin(all_from_nodes))
                ]
        junctions_to_outfalls_map = {
            'Name': 'Name',
            'Elev': 'Elev',
            'geometry': 'geometry',
        }
        gdf_outfalls, outfalls_layername = create_section_from_gdf('Outfalls',
                                                                   crs,
                                                                   gdf_junctions_outfalls,
                                                                   junctions_to_outfalls_map)
        gdf_outfalls['Type'] = 'FIXED'
        # Start with WSE at ground (0.0 depth) will be modified when run inside TUFLOW
        gdf_outfalls['Stage'] = gdf_outfalls['Elev']
        # print(gdf_outfalls)
        feedback.pushInfo(f'Number of outfalls: {len(gdf_outfalls)}')

    # Handle Inlets and related tables
    gdf_pits = None
    if gdf_junction_data is not None:
        pit_inlet_types = ['C', 'Q', 'R', 'W']

        gdf_junction_data['Type'] = gdf_junction_data['Type'].astype(str).str.upper()
        gdf_junction_data['Conn_1D_2D'] = gdf_junction_data['Conn_1D_2D'].astype(str).str.upper()
        gdf_pits = gdf_junction_data[gdf_junction_data['Conn_1D_2D'].astype(str).str.contains('SX')].copy(deep=True)
        # gdf_pits = gdf_junction_data[gdf_junction_data['Type'].isin(pit_inlet_types)].copy(deep=True)

        # For Q inlets, we will use custom curves
        gdf_pit_Q = gdf_pits[gdf_pits['Type'] == 'Q']
        # print(gdf_pit_Q)

        if len(gdf_pit_Q) > 0:
            inlet_q_to_inlets_map = {
                'Name': 'Name',
                'geometry': 'geometry',
            }
            # feedback.pushInfo(gdf_pit_Q.describe().to_string())

            gdf_inlets_q, inlets_layername = create_section_from_gdf('Inlets',
                                                                     crs,
                                                                     gdf_pit_Q,
                                                                     inlet_q_to_inlets_map)

            gdf_inlets_q['Type'] = 'CUSTOM'
            gdf_inlets_q['Custom_Curve'] = gdf_inlets_q['Name']
            # print(gdf_inlets_q)

        # W types weirs - represent as a curb with similar perimeter to width (used as weir length in TUFLOW)
        gdf_pit_W = gdf_pits[gdf_pits['Type'] == 'W']

        if len(gdf_pit_W) > 0:
            feedback.pushInfo(f'Number of W inlets: {len(gdf_pit_W)}')

            grate_widths = sorted(gdf_pit_W['Width'].unique())

            # multiply by 1000 and convert to int to make unique names
            grate_names = [f'W_{int(x * 1000)}' for x in grate_widths]
            # print(grate_names)

            # make the grate lengths equal to the length
            grate_lengths = np.array(grate_widths)

            grate_heights = [5.0] * len(grate_names)

            throat = ['VERTICAL'] * len(grate_widths)

            gdf_inlets_w = gpd.GeoDataFrame(
                {
                    'Name': grate_names,
                    'Type': ['CURB'] * len(grate_names),
                    'Curb_Length': grate_lengths,
                    'Curb_Height': grate_heights,
                    'Curb_Throat': throat,
                    'Grate_Aopen': [np.nan] * len(grate_names),
                    'Grate_vsplash': [np.nan] * len(grate_names),
                    'geometry': None,
                }
            )
            inlet_w_to_inlet_w_map = {
                x: x for x in gdf_inlets_w.columns
            }
            gdf_inlets_w, inlets_layername = create_section_from_gdf('Inlets',
                                                                     crs,
                                                                     gdf_inlets_w,
                                                                     inlet_w_to_inlet_w_map)

        # Inlets type R - R is vertical so it is a curb inlet
        gdf_inlets_r = gdf_pits[gdf_pits['Type'] == 'R']
        if len(gdf_inlets_r) > 0:
            feedback.pushInfo(f'Number of rectangular inlets: {len(gdf_inlets_r)}')

            # print(gdf_inlets_r)

            curb_lengths = gdf_inlets_r['Width_or_Dia']
            curb_heights = gdf_inlets_r['Height_or_WF']

            # print(curb_lengths)
            # print(curb_heights)

            # multiply lengths and heights by 1000 to make names
            inlet_names = [f'{int(x * 1000)}_by_{int(y * 1000)}' for x, y in zip(curb_lengths, curb_heights)]

            r_pits = gdf_pits['Type'].isin(['R', 'r'])
            gdf_pits.loc[r_pits, 'Name'] = inlet_names

            throat = ['VERTICAL'] * len(curb_lengths)

            gdf_inlets_r = gpd.GeoDataFrame(
                {
                    'Name': inlet_names,
                    'Type': ['CURB'] * len(curb_lengths),
                    'Curb_Length': curb_lengths,
                    'Curb_Height': curb_heights,
                    'Curb_Throat': throat,
                    'Grate_Aopen': [np.nan] * len(curb_lengths),
                    'Grate_vsplash': [np.nan] * len(curb_lengths),
                    'geometry': None,
                }
            )
            inlet_r_to_inlet_r_map = {
                x: x for x in gdf_inlets_r.columns
            }
            gdf_inlets_r, inlets_layername = create_section_from_gdf('Inlets',
                                                                     crs,
                                                                     gdf_inlets_r,
                                                                     inlet_r_to_inlet_r_map)
            gdf_inlets_r = gdf_inlets_r.drop_duplicates(subset=['Name'])
            # drop duplicate names

        # Inlets type blank (temporary)
        gdf_inlets_blank = gdf_junction_data[~gdf_junction_data['Type'].isin(pit_inlet_types)]
        if len(gdf_inlets_blank) > 0:
            feedback.pushInfo(f'Number of automatic node connections: {len(gdf_inlets_blank)}')

            # We need to change name here to get into inlet usage
            blank_pits = ~gdf_pits['Type'].isin(pit_inlet_types)
            gdf_pits.loc[blank_pits, 'Name'] = ''
            gdf_pits.loc[blank_pits, 'Pit_elev'] = gdf_pits.loc[blank_pits, 'Invert']

            gdf_inlets_blank = gpd.GeoDataFrame(
                {
                    'Name': [''] * len(gdf_inlets_blank),
                    'Type': ['CURB'] * len(gdf_inlets_blank),
                    'Grate_Length': 0.0,
                    'Grate_Width': 0.0,
                    'Grate_Type': 0.0,
                    'Grate_Aopen': [np.nan] * len(gdf_inlets_blank),
                    'Grate_vsplash': [np.nan] * len(gdf_inlets_blank),
                    'geometry': None,
                }
            )
            inlet_blank_to_inlet_blank_map = {
                x: x for x in gdf_inlets_blank.columns
            }
            gdf_inlets_blank, inlets_layername = create_section_from_gdf('Inlets',
                                                                         crs,
                                                                         gdf_inlets_blank,
                                                                         inlet_blank_to_inlet_blank_map)

        # TODO C types

    gdfs_inlets = [
        gdf_inlets_w,
        gdf_inlets_q,
        gdf_inlets_r,
        gdf_inlets_blank,
    ]
    gdfs_inlets = list(filter(lambda x: x is not None and len(x) > 0, gdfs_inlets))

    if len(gdfs_inlets) > 0:
        gdf_inlets = pd.concat(gdfs_inlets)
    else:
        gdf_inlets = None

    if gdf_inlets is not None:
        gdf_inlets = gdf_inlets[gdf_inlets['Name'] != 'dummy']

    gdf_inlet_usage_ext = None
    gdf_inlet_usage = None
    gdf_streets = None

    if gdf_pits is not None and len(gdf_pits) > 0:
        feedback.pushInfo('Generating inlet usage information')
        gdf_inlet_usage_ext, inlet_usage_ext_layername = create_inlet_usage_table(
            gdf_pits,
            street_name,
            street_slope_pct,
            reference_cell_size,
            crs,
            feedback,
        )

    # Now that we have created the inlet usage table. Delete the blank inlets
    if gdf_inlets is not None:
        gdf_inlets = gdf_inlets[gdf_inlets['Name'] != '']
        if len(gdf_inlets) == 0:
            gdf_inlets = None
            feedback.pushInfo('Only blank connections found. No inlets will be written.')

    gdf_streets, streets_layername = create_section_gdf('Streets', crs)
    gdf_street_info = gpd.GeoDataFrame(
        {
            'Name': street_name,
            'Tcrown': 10,
            'Hcurb': 0.2,
            'Sx': 4.0,
            'nRoad': 0.016,
            'a': 0.0,
            'W': 0.0,
            'Sides': 1,
            'Tback': 5.0,
            'Sback': 8.0,
            'nBack': 0.016
        },
        index=[0],
        geometry=[None],
        crs=crs,
    )
    gdf_streets = pd.concat([gdf_streets, gdf_street_info], axis=0)
    gdf_streets = gdf_streets[1:]  # Remove dummy row

    # Create the curves table based upon the pit_inlet_dbase
    gdf_curves = None
    curves_layername = 'Curves'
    if inlet_dbase is not None:
        gdf_curves, curves_layername = pit_inlet_dbase_to_df(inlet_dbase, crs, feedback)

    # concatenate other sections
    gdfs_all_curves = [gdf_curves, gdf_bridges_bb_curves]
    gdfs_all_curves = list(filter(lambda x: x is not None, gdfs_all_curves))
    if len(gdfs_all_curves) > 0:
        gdf_curves = pd.concat(gdfs_all_curves, ignore_index=True).copy(deep=True)
        gdf_curves.reset_index(drop=True, inplace=True)
    else:
        gdf_curves = None

    # concatenate xsections as needed
    gdfs_all_xsects = [gdf_xsecs, gdf_weir_xsecs, gdf_sg_xsecs, gdf_bridges_bb_xsecs]
    gdfs_all_xsects = list(filter(lambda x: x is not None, gdfs_all_xsects))
    if len(gdfs_all_xsects) > 0:
        gdf_xsecs = pd.concat(gdfs_all_xsects)
    else:
        gdf_xsecs = None

    # Combine tables as needed
    # Merge the XSections table with the conduit, weir, and orifice tables
    if gdf_conduits is not None:
        if gdf_xsecs is not None:
            # We need to drop overlapping columns
            columns_to_drop = [f'xsec_{x}' for x in gdf_xsecs.columns if x != 'geometry']
            columns_to_drop = [x for x in columns_to_drop if x in gdf_conduits.columns]
            gdf_conduits = gdf_conduits.drop(columns=columns_to_drop)
            gdf_conduits2 = gdf_conduits.merge(
                gdf_xsecs.drop(columns=['geometry']).rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdf_conduits = gdf_conduits2.drop(columns=['xsec_Link'])
        else:
            # Add empty cross-section columns
            gdf_conduits.loc[:,
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
        if gdf_losses is not None:
            # We need to drop overlapping columns
            columns_to_drop = [f'losses_{x}' for x in gdf_losses.columns if x != 'geometry']
            columns_to_drop = [x for x in columns_to_drop if x in gdf_conduits.columns]
            gdf_conduits = gdf_conduits.drop(columns=columns_to_drop)
            gdf_conduits2 = gdf_conduits.merge(
                gdf_losses.drop(columns=['geometry']).rename(columns=lambda x: f'losses_{x}'),
                how='left',
                left_on='Name',
                right_on='losses_Link',
            )
            gdf_conduits = gdf_conduits2.drop(columns=['losses_Link'])
        else:
            # add empty columns
            gdf_conduits.loc[:,
            ['losses_Kentry', 'losses_Kexit', 'losses_Kavg', 'losses_Flap', 'losses_Seepage']] = None

    if gdf_weirs is not None:
        if gdf_xsecs is not None:
            # Drop the columns we don't need
            df_weir_xsecs = gdf_xsecs.drop(columns=['geometry',
                                                    'Culvert',
                                                    'Curve',
                                                    'Tsect',
                                                    'Street'])
            # drop duplicate columns
            cols_to_drop = set(gdf_weirs.columns).intersection(
                set(df_weir_xsecs.rename(columns=lambda x: f'xsec_{x}').columns))
            gdf_weirs = gdf_weirs.drop(
                columns=cols_to_drop,
            )
            gdf_weirs2 = gdf_weirs.merge(
                df_weir_xsecs.rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdf_weirs = gdf_weirs2.drop(columns='xsec_Link')
        else:
            # Add the cross-section columns
            gdf_weirs.loc[:,
            ['xsec_XsecType',
             'xsec_Geom1',
             'xsec_Geom2',
             'xsec_Geom3',
             'xsec_Geom4',
             ]] = None

    if gdf_orifices is not None:
        if gdf_xsecs is not None:
            # Drop the columns we don't need (
            df_orifice_xsecs = gdf_xsecs.drop(
                columns=[
                    'geometry',
                    'Culvert',
                    'Curve',
                    'Tsect',
                    'Street'])
            # drop duplicate columns
            cols_to_drop = set(gdf_orifices.columns).intersection(
                set(df_orifice_xsecs.rename(columns=lambda x: f'xsec_{x}').columns))
            gdf_orifices = gdf_orifices.drop(
                columns=cols_to_drop,
            )
            gdf_orifices2 = gdf_orifices.merge(
                df_orifice_xsecs.rename(columns=lambda x: f'xsec_{x}'),
                how='left',
                left_on='Name',
                right_on='xsec_Link',
            )
            gdf_orifices = gdf_orifices2.drop(columns='xsec_Link')
        else:
            # Add the cross-section columns
            gdf_orifices.loc[:,
            ['xsec_XsecType',
             'xsec_Geom1',
             'xsec_Geom2',
             'xsec_Geom3',
             'xsec_Geom4',
             'xsec_Barrels'
             ]] = None
            gdf_orifices.loc[:, 'xsec_Barrels'] = 1

    if create_options_report_tables:
        feedback.pushInfo('Creating options and report tables')
        gdf_options, options_layername = default_options_table(crs, report_step, min_surface_area)

        gdf_options.to_file(swmm_out_filename,
                            layer=options_layername,
                            driver='GPKG')

        gdf_reporting, reporting_layername = default_reporting_table(crs)

        gdf_reporting.to_file(swmm_out_filename,
                              layer=reporting_layername,
                              driver='GPKG')

    if gdf_inlet_usage_ext is not None:
        feedback.pushInfo(f'Writing external inlet usage information to: {ext_inlet_usage_filename}')
        gdf_inlet_usage_ext.to_file(ext_inlet_usage_filename,
                                    layer='inlet_usage',
                                    driver='GPKG')

    if gdf_inlets is not None:
        gdf_inlets['geometry'] = None

    # These are the geo-dataframes and layernames to write to the swmm output file
    # that have dummy rows (reporting and options do not have dummy rows)
    gdfs_layernames = [
        (gdf_junctions, junctions_layername),
        (gdf_conduits, conduits_layername),
        (gdf_pumps, pumps_layername),
        # Now embedded in conduit, weir, orifice tables
        # (gdf_xsecs, xsecs_layername),
        # (gdf_losses, losses_layername),
        (gdf_outfalls, outfalls_layername),
        (gdf_inlets, inlets_layername),
        (gdf_streets, streets_layername),
        (gdf_weirs, weirs_layername),
        (gdf_orifices, orifices_layername),
        (gdf_outlets, outlets_layername),
        (gdf_curves, curves_layername),
    ]

    gdfs_layernames = [(x[0], x[1]) for x in gdfs_layernames if x[0] is not None]
    # print([x[1] for x in gdfs_layernames])

    feedback.pushInfo(f'Writing data to GeoPackage file: {swmm_out_filename}')
    for gdf, layername in gdfs_layernames:
        gdf.to_file(swmm_out_filename,
                    index=False,
                    layer=layername,
                    driver='GPKG')

    # for gdf, layername in gdfs_layernames:
    #     delete_layer_features(swmm_out_filename, layername)

    swmm_inp_filename = Path(swmm_out_filename).with_suffix('.inp')
    gis_to_swmm(swmm_out_filename,
                swmm_inp_filename,
                feedback)


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 300)
    pd.set_option('max_colwidth', 100)

    gis_folder = None

    nwk_layers = []
    node_layers = []
    pit_layers = []
    table_link_layers = []
    pit_inlet_database = None

    # Street information (needed if there are pits)
    street_name = 'DummyStreet'
    street_slope_pct = 4.0
    reference_cell_size = 5.0

    snap_tolerance = 0.001

    create_options_report_tables = True
    report_step = '00:05:00'
    min_surface_area = 25.0

    crs = 'EPSG:28356'

    output_filename = None
    external_gpkg_filename = None

    simulation = ['Bankstown',
                  'OneChannel_base',
                  'OneChannel_pump',
                  'OneChannel_weir',
                  'OneChannel_sluicegate',
                  'OneChannel_qchan',
                  'Bankstown_xs',
                  'Bankstown_pits',
                  ][-1]

    if simulation == 'Bankstown':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\gis')
        nwk_layers = [
            'C13_test_003_ECF.gpkg/1d_nwk_culverts_C13_007_L',
            'C13_test_003_ECF.gpkg/1d_nwk_pipes_C13_012_L',
            'C13_test_003_ECF.gpkg/1d_nwk_junctions_C13_012_P',
            'C13_test_003_ECF.gpkg/1d_nwk_outlets_C13_012_P',
            'C13_test_003_ECF.gpkg/1d_nwk_pits_C13_012_P',
        ]
        node_layers = []  # Need to create some and test or use other model
        pit_layers = []  # Need to create and test
        table_link_layers = [
            'C13_test_003_ECF.gpkg/1d_xs_culvert_C13_005_L',
        ]
        pit_inlet_database = \
            r"D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\pit_dbase\BIV_pit_dbase_001B.csv"
        r"D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\pit_dbase\BIV_pit_dbase_001B.csv"
        output_filename = r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\SWMM\test_export_layers'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'
    elif simulation == 'OneChannel_base':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\gis')
        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_estry_chan_001_L',
        ]
        node_layers = [
            'onechan_inputs.gpkg/1d_nd_estry_001_P',
        ]
        pit_layers = []  # Need to create and test
        table_link_layers = []
        pit_inlet_database = None

        output_filename = r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\SWMM\test_export_base'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

        crs = 'EPSG:32760'
    elif simulation == 'OneChannel_pump':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\gis')
        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_estry_pump_005_L',
        ]
        node_layers = [
            'onechan_inputs.gpkg/1d_nd_estry_001_P',
        ]
        pit_layers = []  # Need to create and test
        table_link_layers = []
        pit_inlet_database = None

        output_filename = r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\SWMM\test_export_pump'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

        crs = 'EPSG:32760'
    elif simulation == 'OneChannel_weir':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\gis')
        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_weir01_006_L',
        ]
        node_layers = [
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        pit_layers = []  # Need to create and test
        table_link_layers = []
        pit_inlet_database = None

        output_filename = r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\SWMM\test_export_weir'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

        crs = 'EPSG:32760'
    elif simulation == 'OneChannel_sluicegate':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\gis')
        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_sg01_006_L',
        ]
        node_layers = [
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        pit_layers = []  # Need to create and test
        table_link_layers = []
        pit_inlet_database = None

        output_filename = r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\SWMM\test_export_sluicegate'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

        crs = 'EPSG:32760'
    elif simulation == 'OneChannel_qchan':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\gis')
        nwk_layers = [
            'onechan_inputs.gpkg/1d_nwk_qchan01_006_L',
        ]
        node_layers = [
            'onechan_inputs.gpkg/1d_nd_extra_weir_001_P',
        ]
        pit_layers = []  # Need to create and test
        table_link_layers = []
        pit_inlet_database = None

        output_filename = r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\model\SWMM\test_export_qchan'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

        crs = 'EPSG:32760'
    elif simulation == 'Bankstown_xs':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\gis')
        nwk_layers = [
        ]
        node_layers = []  # Need to create some and test or use other model
        pit_layers = []  # Need to create and test
        table_link_layers = [
            'C13_test_003_ECF.gpkg/1d_xs_culvert_C13_005_L',
        ]
        pit_inlet_database = None
        output_filename = r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\SWMM\test_export_layers'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'
    elif simulation == 'Bankstown_pits':
        gis_folder = Path(r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\gis')
        nwk_layers = [
        ]
        node_layers = []  # Need to create some and test or use other model
        pit_layers = []  # Need to create and test
        table_link_layers = [
        ]
        pit_inlet_database = \
            r"D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\pit_dbase\BIV_pit_dbase_001B.csv"
        output_filename = r'D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW\model\SWMM\test_export_layers'
        external_gpkg_filename = f'{output_filename}_ext'
        output_filename = output_filename + '.gpkg'
        external_gpkg_filename = external_gpkg_filename + '.gpkg'

    # convert to full path filenames
    nwk_layers = [gis_folder / nwk_layer for nwk_layer in nwk_layers]
    node_layers = [gis_folder / layer for layer in node_layers]
    pit_layers = [gis_folder / layer for layer in pit_layers]
    table_link_layers = [gis_folder / layer for layer in table_link_layers]

    convert_layers(nwk_layers, node_layers, pit_layers, table_link_layers,
                   pit_inlet_database,
                   street_name, street_slope_pct, reference_cell_size,
                   create_options_report_tables, report_step, min_surface_area,
                   snap_tolerance,
                   output_filename, external_gpkg_filename,
                   crs)
