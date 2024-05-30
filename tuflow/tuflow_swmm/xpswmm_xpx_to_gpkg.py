from collections import defaultdict
from enum import Enum
import math
from pathlib import Path

import csv
import datetime
import geopandas as gpd
import json
import numpy as np
import pandas as pd
import re
from shapely.geometry import LineString, Polygon

from tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow_swmm.create_swmm_section_gpkg import create_section_gdf
from tuflow_swmm.estry_to_swmm_model import create_curves_from_dfs
from tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow_swmm.junctions_downstream_to_outfalls import downstream_junctions_to_outfalls
from tuflow_swmm.swmm_sanitize import sanitize_name
from tuflow_swmm.xpswmm_node2d_convert import xpswmm_2d_capture_to_swmm_gpd
import tuflow_swmm.swmm_io as swmm_io
from tuflow_swmm.xpswmm_xpx_to_gpkg_tables import get_nearest_width_for_horzellipse, get_arch_width


class SwmmTableEnum(Enum):
    JUNCTIONS = 1
    STORAGE_NODES = 2
    OUTFALLS = 3
    CONDUITS = 4
    SUBCATCMENTS = 5
    RAINGAGES = 6
    INLETS = 7


def handle_date_time_fields(options_data, options_key_array, options_value_array, feedback, prefix, date_fields):
    date_error = False
    for start_date_entry in date_fields:
        if start_date_entry not in options_data:
            feedback.pushWarning(f'Required date entry not found: {start_date_entry}')
            date_error = True
    if not date_error:
        start_date = datetime.datetime(*[options_data[date_fields[i]] for i in range(5)])
        options_key_array.append(f'{prefix}_DATE')
        options_value_array.append(start_date.strftime('%m/%d/%Y'))
        options_key_array.append(f'{prefix}_TIME')
        options_value_array.append(start_date.strftime('%H:%M:%S'))


def xpx_to_gpkg(xpx_filename,
                gpkg_filename,
                iu_filename,
                messages_filename,
                crs,
                feedback=ScreenProcessingFeedback()):
    if type(gpkg_filename) == str:
        gpkg_filename = Path(gpkg_filename)

    if type(messages_filename) == str:
        messages_filename = Path(messages_filename)

    node_names = []
    node_x = []
    node_y = []

    outfall_nodes = set()
    storage_nodes = set()

    inlet_nodes = set()
    # Linked nodes not through inlets
    linked_nodes_sflood3 = set()
    linked_nodes_sflood4 = set()

    links_name = []
    links_node1 = []
    links_node2 = []

    vertices = {}
    cur_vertices_name = None
    cur_vertices = []

    subs_name = []
    subs_vertices = []

    raingages_name = []

    messages_location = []
    messages_severity = []
    messages_text = []

    global_2dlink_settings = {}

    inactive_objects = set()

    # Gather the sections to represent
    with open(xpx_filename, encoding='utf-8', errors='replace') as xpx_file:
        reader = csv.reader(xpx_file, delimiter=' ')
        for i, row in enumerate(reader):
            # line = line.strip()
            # line_vals = re.split('''s(?=(?s[^'"]|'[^']*'|"[^"]*")*$)''', line)
            # line_vals = line.split(' ')
            # line_lower = line.lower()
            # line_vals_lower = line_lower.split(' ')

            line_vals = row
            if len(line_vals) == 0:
                continue
            if line_vals[-1] == '':
                line_vals = line_vals[:-1]
            line_vals_lower = [x.lower() for x in line_vals]

            if line_vals_lower[0] == 'vertex_end':
                vertices[cur_vertices_name] = cur_vertices
                cur_vertices_name = None
                cur_vertices = []
            elif cur_vertices_name is not None:
                cur_vertices.append((float(line_vals[0]), float(line_vals[1])))
            elif line_vals_lower[0] == 'node':
                node_names.append(line_vals[2].strip('"'))
                node_x.append(float(line_vals[3]))
                node_y.append(float(line_vals[4]))
            elif line_vals_lower[0] == 'link':
                links_name.append(line_vals[2].strip('"'))
                links_node1.append(line_vals[3].strip('"'))
                links_node2.append(line_vals[4].strip('"'))
            elif line_vals_lower[0] == 'vertex_start':
                cur_vertices_name = line_vals[2].strip('"')
            elif line_vals_lower[0] == 'catchment':
                sub_name = line_vals[1].strip('"')
                sub_number = int(line_vals[2].strip('"'))
                sub_name = f'{sub_name}#{sub_number}'
                subs_name.append(sub_name)
                pts = []
                npoints = int(line_vals[3])
                for ipoint in range(npoints):
                    nextline = next(xpx_file).strip()
                    nextline_vals = tuple([float(x) for x in nextline.split(' ')])
                    pts.append(nextline_vals)
                subs_vertices.append(pts)
            elif line_vals_lower[0] == 'gldbitem':
                if line_vals_lower[1].strip('"') == 'rainfall':
                    raingages_name.append(line_vals[2])
            elif line_vals_lower[0] == 'data':
                if line_vals_lower[1] == 'flgoutf':
                    if int(line_vals[5]) == 1:
                        outfall_nodes.add(line_vals[2])
                elif line_vals_lower[1] == 'nodst':
                    if int(line_vals[5]) == 1:
                        storage_nodes.add(line_vals[2])
                elif line_vals_lower[1] == '2dinflow_flag':
                    if int(line_vals[5]) == 1:
                        inlet_nodes.add(line_vals[2])
                elif line_vals_lower[1] == 'sflood':
                    if int(line_vals[5]) == 3:
                        linked_nodes_sflood3.add(line_vals[2])
                    elif int(line_vals[5]) == 4:
                        linked_nodes_sflood4.add(line_vals[2])
                elif line_vals_lower[1] == 'jc_2dinflow_expon':
                    global_2dlink_settings['Exponent'] = float(line_vals[5])
                elif line_vals_lower[1] == 'jc_2dinflow_chk':
                    global_2dlink_settings['On'] = int(line_vals[5]) == 1
                elif line_vals_lower[1] == 'jc_2dinflow_coeff':
                    global_2dlink_settings['Coefficient'] = float(line_vals[5])
                elif line_vals_lower[1] == 'locmode':
                    if int(line_vals[5]) == 0:
                        inactive_objects.add(line_vals[2])

    gdf_junctions, junctions_layername = create_section_gdf('Junctions', crs)
    gdf_junctions.drop(gdf_junctions.index, inplace=True)
    gdf_all_nodes = gpd.GeoDataFrame(
        {
            'Name': node_names,
        },
        crs=crs,
        geometry=gpd.points_from_xy(node_x, node_y))


    gdf_junction_values = gdf_all_nodes[(~gdf_all_nodes['Name'].isin(storage_nodes)) &
                                        (~gdf_all_nodes['Name'].isin(outfall_nodes))]
    gdf_junctions = pd.concat([gdf_junctions, gdf_junction_values])

    gdf_storage, storage_layername = create_section_gdf('Storage', crs)
    gdf_storage.drop(gdf_storage.index, inplace=True)
    gdf_storage_node_values = gdf_all_nodes[(gdf_all_nodes['Name'].isin(storage_nodes))]
    gdf_storage = pd.concat([gdf_storage, gdf_storage_node_values])

    gdf_outfalls, outfalls_layername = create_section_gdf('Outfalls', crs)
    gdf_outfalls.drop(gdf_outfalls.index, inplace=True)
    gdf_outfall_node_values = gdf_all_nodes[(gdf_all_nodes['Name'].isin(outfall_nodes))]
    gdf_outfalls = pd.concat([gdf_outfalls, gdf_outfall_node_values])

    if inlet_nodes:
        gdf_inlet_info = gdf_all_nodes[(gdf_all_nodes['Name'].isin(inlet_nodes))].copy(deep=True)
        gdf_inlet_info.loc[:, ['coeff', 'exponent']] = None
    else:
        gdf_inlet_info = None

    # Linked nodes SFLOOD=3 links the node spill crest to 2D. TUFLOW-SWMM requires this to use an inlet
    # If a global 2d linking is on use those. otherwise report an error and the nodes not linked through inlets
    linked_sflood3_noinlet = linked_nodes_sflood3 - inlet_nodes
    if len(linked_sflood3_noinlet) > 0:
        if 'On' in global_2dlink_settings and global_2dlink_settings['On']:
            gdf_inlet_info_sflood3 = gdf_all_nodes[(gdf_all_nodes['Name'].isin(linked_sflood3_noinlet))].copy(deep=True)
            gdf_inlet_info_sflood3.loc[:, 'coeff'] = global_2dlink_settings['Coefficient']
            gdf_inlet_info_sflood3.loc[:, 'exponent'] = global_2dlink_settings['Exponent']
            if gdf_inlet_info is None:
                gdf_inlet_info = gdf_inlet_info_sflood3
            else:
                gdf_inlet_info = pd.concat([gdf_inlet_info, gdf_inlet_info_sflood3])
        else:
            feedback.reportError('Nodes connected to 2D using the spill crest elevation without an inlet exist. These '
                                 'must converted to use inlets for TUFLOW-SWMM. See the messages file.')
            for row in gdf_all_nodes[gdf_all_nodes['Name'].isin(linked_sflood3_noinlet)].itertuples(index=False):
                messages_location.append(row.geometry)
                messages_severity.append('ERROR')
                messages_text.append(
                    f'Node {row.Name} is linked to 2D at the spill crest elevation without an inlet as '
                    f'required by TUFLOW-SWMM.')

    # Linked nodes FLOOD=4 links the node invert to 2D. These are usually connected with HX/SX line in separate layer
    if len(linked_nodes_sflood4) > 0:
        for row in gdf_all_nodes[gdf_all_nodes['Name'].isin(linked_nodes_sflood4)].itertuples(index=False):
            messages_location.append(row.geometry)
            messages_severity.append('INFO')
            messages_text.append(f'Node {row.Name} is linked to 2D at the invert elevation should be connected using '
                                 f'HX or SX in a 2d_bc layer')

    # Defaults
    if gdf_inlet_info is not None:
        gdf_inlet_info.loc[:, 'ground'] = 0.0
        gdf_inlet_info.loc[:, 'flag'] = 1

    # Build conduits from nodes and vertices
    conduit_geom = []
    for link_name, link_node1, link_node2 in zip(links_name, links_node1, links_node2):
        pts = []
        pts.append(
            (gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node1, 'geometry'].x,
             gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node1, 'geometry'].y)
        )
        if link_name in vertices:
            for vertex in vertices[link_name]:
                pts.append(vertex)
        pts.append(
            (gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node2, 'geometry'].x,
             gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node2, 'geometry'].y)
        )
        conduit_geom.append(LineString(pts))

    gdf_conduits, conduits_layername = create_section_gdf('Conduits', crs)
    gdf_conduits.drop(gdf_conduits.index, inplace=True)
    gdf_conduit_values = gpd.GeoDataFrame(
        {
            'Name': links_name,
            'From Node': links_node1,
            'To Node': links_node2,
        },
        crs=crs,
        geometry=conduit_geom)

    gdf_conduits = pd.concat([gdf_conduits, gdf_conduit_values])

    # Build subcatchments
    subs_geom = []
    for sub_name, sub_vertices in zip(subs_name, subs_vertices):
        subs_geom.append(Polygon(np.array(sub_vertices)))

    gdf_subs, sub_layername = create_section_gdf('Subcatchments', crs)
    gdf_subs.drop(gdf_subs.index, inplace=True)
    gdf_subs_values = gpd.GeoDataFrame(
        {
            'Name': subs_name,
        },
        crs=crs,
        geometry=subs_geom)

    gdf_subs = pd.concat([gdf_subs, gdf_subs_values])

    gdf_raingages, raingages_layername = create_section_gdf('Raingages', crs)
    gdf_raingages.drop(gdf_raingages.index, inplace=True)
    gdf_raingages_values = gpd.GeoDataFrame(
        {
            'Name': raingages_name,
        },
        crs=crs,
        geometry=len(raingages_name) * [None],
    )
    gdf_raingages = pd.concat([gdf_raingages, gdf_raingages_values])

    gdf_title, title_layername = create_section_gdf('Title', crs)
    gdf_title.drop(gdf_title.index, inplace=True)

    gdf_timeseries, timeseries_layername = create_section_gdf('Timeseries', crs)
    gdf_timeseries.drop(gdf_timeseries.index, inplace=True)

    # defaults
    gdf_junctions['Y0'] = 0.0
    gdf_junctions['Ysur'] = 0.0
    gdf_junctions['Apond'] = 0.0

    gdf_storage['Acurve'] = None
    gdf_storage['A1'] = 0.0
    gdf_storage['A2'] = 0.0
    gdf_storage['A0'] = 0.0

    gdf_outfalls['Type'] = ''
    gdf_outfalls['Stage'] = 0.0

    # default some values
    gdf_conduits['nkctl'] = 0
    gdf_conduits['xsec_XsecType'] = '1'
    gdf_conduits['xsec_Geom1'] = 0.0
    gdf_conduits['xsec_Geom2'] = 0.0
    gdf_conduits['xsec_Geom3'] = 0.0
    gdf_conduits['xsec_Geom4'] = 0.0
    gdf_conduits['xsec_Barrels'] = 1
    gdf_conduits['xsec_Tsect'] = ''
    gdf_conduits['losses_Kentry'] = 0.0
    gdf_conduits['losses_Kexit'] = 0.0
    gdf_conduits['losses_Kavg'] = 0.0
    gdf_conduits['Active'] = 1

    if len(gdf_subs) > 0:
        gdf_subs['Outlet'] = gdf_subs['Name'].str.split('#', n=1, expand=True)[0]
        gdf_subs['Subareas_RouteTo'] = 'OUTLET'
        gdf_subs['CurbLen'] = 0.0
        gdf_subs['SnowPack'] = None  # Name of snowpack item
        gdf_subs.loc[:, ['Infiltration_p1', 'Infiltration_p2', 'Infiltration_p3', 'Infiltration_p4']] = 0.0

    gdf_raingages['SnowCatchDeficiency'] = 1.0

    swmm_tables = {
        SwmmTableEnum.JUNCTIONS: gdf_junctions,
        SwmmTableEnum.STORAGE_NODES: gdf_storage,
        SwmmTableEnum.OUTFALLS: gdf_outfalls,
        SwmmTableEnum.CONDUITS: gdf_conduits,
        SwmmTableEnum.SUBCATCMENTS: gdf_subs,
        SwmmTableEnum.RAINGAGES: gdf_raingages,
        SwmmTableEnum.INLETS: gdf_inlet_info,
    }

    feedback.pushInfo(f'Number of nodes: {len(node_names)}')
    feedback.pushInfo(f'  Number of junctions: {len(gdf_junctions)}')
    feedback.pushInfo(f'  Number of storage nodes: {len(gdf_storage)}')
    feedback.pushInfo(f'  Number of outfalls: {len(gdf_outfalls)}')
    feedback.pushInfo(f'Number of links: {len(links_name)}')
    feedback.pushInfo(f'Number of Subcatchments: {len(subs_name)}')

    # for the data entries we will store a mapping (headings converted to lowercase)
    # ((h1, h2, et), table_type(node, conduit, etc), column, name_col, val_type, val_col)

    data_entries = [
        # Junctions
        [('data', 'y0'), SwmmTableEnum.JUNCTIONS, 'Y0', 2, float, 5],
        # [('data', 'e_maxsurcharge'), 'Y1', 2, 5], # not used
        [('data', 'z'), SwmmTableEnum.JUNCTIONS, 'Elev', 2, float, 5],
        [('data', 'grelev'), SwmmTableEnum.JUNCTIONS, 'Ymax', 2, float, 5],

        # Storage nodes
        [('data', 'z'), SwmmTableEnum.STORAGE_NODES, 'Elev', 2, float, 5],
        [('data', 'y0'), SwmmTableEnum.STORAGE_NODES, 'Y0', 2, float, 5],
        [('data', 'grelev'), SwmmTableEnum.STORAGE_NODES, 'Ymax', 2, float, 5],
        [('data', 'cntls'), SwmmTableEnum.STORAGE_NODES, 'TYPE', 2, int, 5],
        [('data', 'astore'), SwmmTableEnum.STORAGE_NODES, 'A1', 2, float, 5],
        [('data', 'const'), SwmmTableEnum.STORAGE_NODES, 'A2', 2, float, 5],
        [('data', 'expo'), SwmmTableEnum.STORAGE_NODES, 'A0', 2, float, 5],

        # Outfalls
        [('data', 'z'), SwmmTableEnum.OUTFALLS, 'Elev', 2, float, 5],
        [('data', 'gate'), SwmmTableEnum.OUTFALLS, 'Gated', 2, str, 5],
        [('data', 'a1a'), SwmmTableEnum.OUTFALLS, 'Stage', 2, float, 5],
        [('data', 'ntide'), SwmmTableEnum.OUTFALLS, 'Type', 2, str, 5],

        # Conduits
        [('data', 'len'), SwmmTableEnum.CONDUITS, 'Length', 2, float, 5],
        [('data', 'rough'), SwmmTableEnum.CONDUITS, 'Roughness', 2, float, 5],
        [('data', 'zp1'), SwmmTableEnum.CONDUITS, 'InOffset', 2, float, 5],
        [('data', 'zp2'), SwmmTableEnum.CONDUITS, 'OutOffset', 2, float, 5],
        [('data', 'qo'), SwmmTableEnum.CONDUITS, 'InitFlow', 2, float, 5],
        [('data', 'locmode'), SwmmTableEnum.CONDUITS, 'Active', 2, int, 5],

        # XSection information
        [('data', 'nklass'), SwmmTableEnum.CONDUITS, 'xsec_XsecType', 2, str, 5],
        [('data', 'nkctl'), SwmmTableEnum.CONDUITS, 'nkctl', 2, str, 5],
        # [('data', 'qmax'), SwmmTableEnum.CONDUITS, 'MaxFlow', 2, float, 5], doesn't seem right
        [('data', 'deep'), SwmmTableEnum.CONDUITS, 'xsec_Geom1', 2, float, 5],
        [('data', 'wide'), SwmmTableEnum.CONDUITS, 'xsec_Geom2', 2, float, 5],
        [('data', 'barrel'), SwmmTableEnum.CONDUITS, 'xsec_Barrels', 2, lambda x: math.floor(float(x)) if x else '', 5],
        [('data', 'plc'), SwmmTableEnum.CONDUITS, 'losses_Kentry', 2, float, 5],
        [('data', 'geoff'), SwmmTableEnum.CONDUITS, 'losses_Kexit', 2, float, 5],
        [('data', 'ttheta'), SwmmTableEnum.CONDUITS, 'xsec_Geom3', 2, float, 5],
        [('data', 'tphi'), SwmmTableEnum.CONDUITS, 'xsec_Geom4', 2, float, 5],
        [('data', 'ptheta'), SwmmTableEnum.CONDUITS, 'xsec_Geom3', 2, float, 5],
        [('data', 'nats_shape'), SwmmTableEnum.CONDUITS, 'xsec_Tsect', 2, lambda x: f'"{x}"' if x else '', 5],

        # Subcatchments
        [('data', 'r_rainsel'), SwmmTableEnum.SUBCATCMENTS, 'Rain Gage', 2, str, 5],
        [('data', 'r_warea'), SwmmTableEnum.SUBCATCMENTS, 'Area', 2, float, 5],
        [('data', 'r_wimp'), SwmmTableEnum.SUBCATCMENTS, 'PctImperv', 2, float, 5],
        [('data', 'r_width'), SwmmTableEnum.SUBCATCMENTS, 'Width', 2, float, 5],
        [('data', 'r_wslope'), SwmmTableEnum.SUBCATCMENTS, 'PctSlope', 2, float, 5],
        [('data', 'r_infilsel'), SwmmTableEnum.SUBCATCMENTS, 'Tag', 2, str, 5],  # Temporarily store infiltration type

        # Raingages
        [('gldbdata', 'r_thisto', 'rainfall'), SwmmTableEnum.RAINGAGES, 'Intvl', 3, float, 5],
        [('gldbdata', 'r_kprepc', 'rainfall'), SwmmTableEnum.RAINGAGES, 'Form', 3, str, 5],

        # Inlets
        [('data', 'grelev'), SwmmTableEnum.INLETS, 'elev', 2, float, 5],
        [('data', 'hdr_2dinflow_expon'), SwmmTableEnum.INLETS, 'exponent', 2, float, 5],
        [('data', 'hdr_2dinflow_coeff'), SwmmTableEnum.INLETS, 'coeff', 2, float, 5],
    ]

    # Set the types
    for headings, entry_type, entry_col, entry_name_col, entry_val_type, entry_val_col in data_entries:
        if swmm_tables[entry_type] is None:
            continue
        if entry_col in swmm_tables[entry_type]:
            if entry_val_type in [str, float, int]:
                swmm_tables[entry_type][entry_col] = swmm_tables[entry_type][entry_col].astype(entry_val_type)
        else:
            swmm_tables[entry_type][entry_col] = entry_val_type() if entry_val_type in [str, float, int] else\
                entry_val_type(None)

    # curve data
    curve_data = defaultdict(dict)
    transect_data = defaultdict(dict)
    ts_data = defaultdict(dict)

    # For options data we will have similar search approach but stick the values in the options dictionary
    options_entries = [
        [('data', 'yzero'), 'start_year', int, 5],
        [('data', 'mozero'), 'start_month', int, 5],
        [('data', 'dzero'), 'start_day', int, 5],
        [('data', 'hzero'), 'start_hour', int, 5],
        [('data', 'mzero'), 'start_minute', int, 5],
        [('data', 'szero'), 'start_second', int, 5],
        [('data', 'ysl'), 'end_year', int, 5],
        [('data', 'mosl'), 'end_month', int, 5],
        [('data', 'dsl'), 'end_day', int, 5],
        [('data', 'hsl'), 'end_hour', int, 5],
        [('data', 'msl'), 'end_minute', int, 5],
        [('data', 'ssl'), 'end_second', int, 5],
        [('data', 'saveres'), 'output_frequency', float, 5],
        [('data', 'alpha'), 'title', str, 5],
        [('data', 'metric'), 'metric', int, 5],
    ]
    options_data = {}

    # for infiltration entries are similar to data_entries but use name lookup in subcatchments
    # ((h1, h2, et), column, name_col, val_type, val_col)
    infiltration_entries = [
        [('gldbdata', 'r_suct', 'infiltration'), 'Infiltration_p1', 3, float, 5],
        [('gldbdata', 'r_hydcon', 'infiltration'), 'Infiltration_p2', 3, float, 5],
        [('gldbdata', 'r_smdmax', 'infiltration'), 'Infiltration_p3', 3, float, 5],
        [('gldbdata', 'r_irough', 'infiltration'), 'Subareas_Nimp', 3, float, 5],
        [('gldbdata', 'r_prough', 'infiltration'), 'Subareas_Nperv', 3, float, 5],
        [('gldbdata', 'r_wstor1', 'infiltration'), 'Subareas_Simp', 3, float, 5],
        [('gldbdata', 'r_wstor2', 'infiltration'), 'Subareas_Sperv', 3, float, 5],
        [('gldbdata', 'r_pctzer', 'infiltration'), 'Subareas_PctZero', 3, float, 5],
    ]

    # defaults
    options_data['save_results'] = 300.0

    # fill in additional data in pass #2
    with open(xpx_filename, encoding='utf-8', errors='ignore') as xpx_file:
        reader = csv.reader(xpx_file, delimiter=' ')
        for row in reader:
            # line = line.strip()
            # line_vals = re.split('''s(?=(?s[^'"]|'[^']*'|"[^"]*")*$)''', line)
            # line_vals = line.split(' ')
            # line_lower = line.lower()
            # line_vals_lower = line_lower.split(' ')

            line_vals = row
            if len(line_vals) == 0:
                continue
            if line_vals[-1] == '':
                line_vals = line_vals[:-1]
            line_vals_lower = [x.lower() for x in line_vals]

            for headings, entry_type, entry_col, entry_name_col, entry_val_type, entry_val_col in data_entries:
                matches = True
                for icol, heading in enumerate(headings):
                    if len(line_vals) < icol + 1:
                        matches = False
                        break
                    elif line_vals_lower[icol] != heading:
                        matches = False
                        break
                if matches:
                    item_name = line_vals[entry_name_col]
                    # for subcatchments we always need the number
                    if entry_type == SwmmTableEnum.SUBCATCMENTS:
                        item_name = f'{item_name}#{int(line_vals[3]) + 1}'
                    item_val = entry_val_type(line_vals[entry_val_col])
                    # feedback.pushDebugInfo(f'Found data: {item_name}: {entry_col} {item_val}')
                    if swmm_tables[entry_type] is not None:
                        swmm_tables[entry_type].loc[swmm_tables[entry_type]['Name'] == item_name, entry_col] = item_val

            # extract options data
            for headings, entry_name, entry_val_type, entry_val_col in options_entries:
                matches = True
                for icol, heading in enumerate(headings):
                    if len(line_vals) < icol + 1:
                        matches = False
                        break
                    elif line_vals_lower[icol] != heading:
                        matches = False
                        break
                if matches:
                    item_val = entry_val_type(line_vals[entry_val_col])
                    options_data[entry_name] = item_val

            # Need to read curve data with R_REIN and R_RMULT
            if line_vals_lower[0] == 'gldbdata' and line_vals_lower[1] == 'r_rein' \
                    and line_vals_lower[2] == 'rainfall':
                ts_name = line_vals[3]
                ts_data[ts_name]['type'] = 'rainfall'
                ts_values = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['values'] = ts_values
            elif line_vals_lower[0] == 'gldbdata' and line_vals_lower[1] == 'r_rmult' \
                    and line_vals_lower[2] == 'rainfall':
                ts_name = line_vals[3]
                ts_data[ts_name]['multiplier'] = float(line_vals[5])

            # inflows
            if line_vals_lower[0] == 'data' and line_vals_lower[1] == 'teo':
                ts_name = line_vals[2] + '_inflow'
                ts_times = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['type'] = 'inflow'
                ts_data[ts_name]['times'] = ts_times
            elif line_vals_lower[0] == 'data' and line_vals_lower[1] == 'qcard':
                ts_name = line_vals[2] + '_inflow'
                ts_values = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['values'] = ts_values

            # transects
            transect_fields_lc = ['el', 'sta', 'nsgd_stchr', 'nsgd_stchl', 'nsgd_xnch', 'nsgd_xnr', 'nsgd_xnl']
            if line_vals_lower[0] == 'gldbdata':
                if line_vals_lower[1] in transect_fields_lc and line_vals_lower[2].strip(
                        '"') == 'natural section shape':
                    transect_name = line_vals[3]
                    if line_vals_lower[1] == 'el':
                        transect_data[transect_name]['Elevations'] = [float(x) for x in line_vals[5:]]
                    elif line_vals_lower[1] == 'sta':
                        transect_data[transect_name]['Stations'] = [float(x) for x in line_vals[5:]]
                    elif line_vals_lower[1] == 'nsgd_stchr':
                        transect_data[transect_name]['Xright'] = float(line_vals[5])
                    elif line_vals_lower[1] == 'nsgd_stchl':
                        transect_data[transect_name]['Xleft'] = float(line_vals[5])
                    elif line_vals_lower[1] == 'nsgd_xnch':
                        transect_data[transect_name]['Nchanl'] = float(line_vals[5])
                    elif line_vals_lower[1] == 'nsgd_xnr':
                        transect_data[transect_name]['Nright'] = float(line_vals[5])
                    elif line_vals_lower[1] == 'nsgd_xnl':
                        transect_data[transect_name]['Nleft'] = float(line_vals[5])

            # conduit hw curves
            if line_vals_lower[0] == 'data' and line_vals_lower[1] == 'dep':
                curve_name = line_vals[2] + '_hw'
                curve_x = [float(x) for x in line_vals[5:]]
                curve_data[curve_name]['Type'] = 'SHAPE'
                curve_data[curve_name]['Depth'] = curve_x
            elif line_vals_lower[0] == 'data' and line_vals_lower[1] == 'sw':
                curve_name = line_vals[2] + '_hw'
                curve_y = [float(x) for x in line_vals[5:]]
                curve_data[curve_name]['Width'] = curve_y

            # Read and apply infiltration parameters
            for headings, entry_col, entry_name_col, entry_val_type, entry_val_col in infiltration_entries:
                matches = True
                for icol, heading in enumerate(headings):
                    if len(line_vals) < icol + 1:
                        matches = False
                        break
                    elif line_vals_lower[icol] != heading:
                        matches = False
                        break
                if matches:
                    item_name = line_vals[entry_name_col]
                    item_val = entry_val_type(line_vals[entry_val_col])
                    gdf_subs.loc[gdf_subs['Tag'] == item_name, entry_col] = item_val

    # Do additional data manipulations
    gdf_junctions['Ymax'] = gdf_junctions['Ymax'] - gdf_junctions['Elev']

    xpx_ntide_to_swmm_outfall = {
        '1': 'FIXED',
        '2': 'NORMAL',
    }
    gdf_unsupported_outfall_rows = gdf_outfalls['Type'].isin(('3', '4', '5'))
    if len(gdf_unsupported_outfall_rows) > 0:
        feedback.pushWarning('Outfall curves are not yet supported in XPX to GPKG converter. See messages file.')
        # Add information for the messages file
        for row in gdf_outfalls.loc[gdf_unsupported_outfall_rows, ('geometry', 'Name')].itertuples():
            messages_location.append(row.geometry)
            messages_severity.append('ERROR')
            messages_text.append(f'Outlet {row.Name} has an outfall with a curve. These are not currently converted '
                                 f'and must be filled in manually.')

    gdf_outfalls['Type'] = gdf_outfalls['Type'].apply(lambda x: xpx_ntide_to_swmm_outfall[x])

    integer_to_yes_no = {
        0: 'No',
        1: 'Yes',
    }
    gdf_outfalls['Gated'] = gdf_outfalls['Gated'].apply(lambda x: integer_to_yes_no[int(x)])

    gdf_storage_invalid_rows = gdf_storage[gdf_storage['TYPE'] == 3]
    if len(gdf_storage_invalid_rows) > 0:
        feedback.pushWarning('Stepwise linear values not yet supported in XPX to GPKG converter.')
    gdf_storage['TYPE'] = 'FUNCTIONAL'

    # Identify inactive nodes
    inactive_node_message_given = False
    if len(inactive_objects) > 0:
        node_tables = [x for x in [gdf_junctions, gdf_storage, gdf_outfalls] if x is not None]
        for node_table in node_tables:
            gdf_inactive_nodes = node_table[node_table['Name'].isin(inactive_objects)]
            if len(gdf_inactive_nodes) > 0:
                if not inactive_node_message_given:
                    feedback.reportError(f'Inactive nodes encountered which will be ignored.')
                    inactive_node_message_given = True

                # Add information for the messages file
                for row in gdf_inactive_nodes[['Name', 'geometry']].itertuples():
                    messages_location.append(row.geometry)
                    messages_severity.append('WARNING')
                    messages_text.append(f'Inactive node {row.Name} ignored.')

            node_table.drop(node_table[node_table['Name'].isin(inactive_objects)].index, inplace=True)

    # Remove inactive conduits
    gdf_inactive_conduits = gdf_conduits[gdf_conduits['Active'] == 0].copy(deep=True)
    if len(gdf_inactive_conduits) > 0:
        feedback.reportError(
            f'Inactive conduits encountered which will be ignored. To convert these conduits first active them in '
            f'XPSWMM.')

        # Add information for the messages file
        for row in gdf_inactive_conduits[['Name', 'geometry']].itertuples():
            messages_location.append(row.geometry.centroid)
            messages_severity.append('WARNING')
            messages_text.append(f'Inactive conduit {row.Name} ignored.')

    gdf_conduits = gdf_conduits[gdf_conduits['Active'] == 1].copy(deep=True).drop(columns=['Active'])

    xpx_shape_to_swmm = {
        1: 'CIRCULAR',
        2: 'RECT_CLOSED',
        3: 'VARIES',
        6: 'TRAPEZOIDAL',
        7: 'POWER',
        8: 'IRREGULAR',
        13: 'CUSTOM',
    }

    # Type 3 above types are based on nkctl
    xpx_shape3_from_nkctl = {
        3: 'HORSESHOE',
        4: 'EGG',
        5: 'BASKETHANDLE',
        14: 'GOTHIC',
        15: 'CATENARY',
        16: 'SEMIELLIPTICAL',
        17: 'SEMICIRCULAR',
        18: 'MODBASKETHANDLE',
        19: 'RECT_TRIANGULAR',
        20: 'RECT_ROUND',
        28: 'HORIZ_ELLIPSE',
        29: 'VERT_ELLIPSE',
        30: 'ARCH',
    }
    if len(gdf_conduits[gdf_conduits['xsec_XsecType'].isna()]) > 0:
        feedback.pushWarning('Invalid or blank cross-section types encountered. These will be assigned to circular.')
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'].isna(), 'xsec_XsecType'] = 1
    gdf_conduits['xsec_XsecType'] = gdf_conduits['xsec_XsecType'].apply(lambda x: xpx_shape_to_swmm[int(x)])
    # Type 3 (Varies) needs a secondary mapping
    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'VARIES', 'xsec_XsecType'] = gdf_conduits.loc[
        gdf_conduits['xsec_XsecType'] == 'VARIES', 'nkctl'
    ].apply(lambda x: xpx_shape3_from_nkctl[int(x)])
    gdf_conduits = gdf_conduits.drop(columns=['nkctl'])

    # Handle ellipses
    using_metric_units = 'metric' in options_data and options_data['metric'] == 1

    # horizontal ellipses are flipped
    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom2'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom1']
    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom1'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom2'].apply(
            lambda x: get_nearest_width_for_horzellipse(using_metric_units, x)
        )

    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'VERT_ELLIPSE', 'xsec_Geom2'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'VERT_ELLIPSE', 'xsec_Geom1'].apply(
            lambda x: get_nearest_width_for_horzellipse(using_metric_units, x)
        )

    # Arch widths - only do if blank
    gdf_conduits.loc[
        (gdf_conduits['xsec_XsecType'] == 'ARCH') & (gdf_conduits['xsec_Geom2'] == 0.0),
        'xsec_Geom2'
    ] = \
        gdf_conduits.loc[
            (gdf_conduits['xsec_XsecType'] == 'ARCH') & (gdf_conduits['xsec_Geom2'] == 0.0),
            'xsec_Geom1'
        ].apply(
            lambda x: get_arch_width(using_metric_units, x)
        )

    # Give a message if modbaskethandle encountered with a width of 0.0
    gdf_modbasket_nowidth = gdf_conduits[
        (gdf_conduits['xsec_XsecType'] == 'MODBASKETHANDLE') & (gdf_conduits['xsec_Geom2'] == 0.0)]
    if len(gdf_modbasket_nowidth) > 0:
        feedback.reportError(
            f'Modified-basket handle geometry encountered without a width assigned. Please review these conduits and '
            f'assign appropriate widths.')

        # Add information for the messages file
        for row in gdf_modbasket_nowidth[['geometry', 'Name']].itertuples():
            messages_location.append(row.geometry.centroid)
            messages_severity.append('ERROR')
            messages_text.append(f'The width for modified basket handle conduit {row.Name} was not written to the '
                                 f'file and must be filled in manually.')

    gdf_subs['PctSlope'] = gdf_subs['PctSlope'] * 100.0
    gdf_subs['Tag'] = None

    gdf_raingages['Intvl'] = gdf_raingages['Intvl'] / 60.0
    xpx_rain_form_to_swmm = {
        0: 'INTENSITY',
        1: 'VOLUME',
        2: 'CUMULATIVE',
    }
    gdf_raingages['Form'] = gdf_raingages['Form'].apply(lambda x: xpx_rain_form_to_swmm[int(x)])
    gdf_raingages['Format'] = 'TIMESERIES'
    gdf_raingages['Tseries'] = gdf_raingages['Name'] + '_rf'

    options_key_array = []
    options_value_array = []

    start_fields = ['start_year', 'start_month', 'start_day', 'start_hour', 'start_minute', 'start_second']
    handle_date_time_fields(options_data, options_key_array, options_value_array, feedback, 'START', start_fields)

    end_fields = ['end_year', 'end_month', 'end_day', 'end_hour', 'end_minute', 'end_second']
    handle_date_time_fields(options_data, options_key_array, options_value_array, feedback, 'END', end_fields)

    options_key_array.append('REPORT_STEP')
    output_freq_s = math.floor(options_data['output_frequency'])
    hours = output_freq_s // 3600
    minutes = (output_freq_s - hours * 3600) // 60
    seconds = (output_freq_s - hours * 3600) % 60
    options_value_array.append(f'{hours:02}:{minutes:02}:{seconds:02}')

    if 'metric' in options_data and options_data['metric'] == 1:
        options_key_array.append('FLOW_UNITS')
        options_value_array.append('CMS')
    else:
        options_key_array.append('FLOW_UNITS')
        options_value_array.append('CFS')

    options_key_array.append('INFILTRATION')
    options_value_array.append('GREEN_AMPT')  # TODO get infiltration approach from xpx file
    options_key_array.append('FORCE_MAIN_EQUATION')
    options_value_array.append('H-W')
    options_key_array.append('FLOW_ROUTING')
    options_value_array.append('DYNWAVE')
    options_key_array.append('ALLOW_PONDING')
    options_value_array.append('YES')
    options_key_array.append('ROUTING_STEP')
    options_value_array.append('00:00:01')
    options_key_array.append('LINK_OFFSETS')
    options_value_array.append('ELEVATION')

    df_options = pd.DataFrame(
        {
            'Option': options_key_array,
            'Value': options_value_array,
        }
    )

    # get the title
    if 'Title' in options_data:
        gdf_title.iloc[0] = options_data['Title']

    # Hanle time-series curves
    ts_curve_names = []
    ts_curve_times = []
    ts_curve_values = []
    for ts_name, ts_curve_data in ts_data.items():
        if ts_curve_data['type'] == 'inflow':
            times = np.array(ts_curve_data['times'])
        else:  # rainfall data
            interval = gdf_raingages.loc[gdf_raingages['Name'] == ts_name, 'Intvl'].iloc[0]
            times = np.arange(0.0, interval * (len(ts_curve_data['values']) + 1), interval)

        values = np.array(ts_curve_data['values'])
        if ts_curve_data['type'] == 'rainfall':
            # add a 0 at the end
            ts_name = ts_name + '_rf'
            values = np.append(values, np.array([0.0]), axis=0)
        if 'multiplier' in ts_curve_data:
            values *= ts_curve_data['multiplier']

        ts_curve_names = ts_curve_names + [ts_name] * len(times)
        ts_curve_times = ts_curve_times + list(times)
        ts_curve_values = ts_curve_values + list(values)

    gdf_timeseries_values = None
    if ts_curve_names:
        gdf_timeseries_values = gpd.GeoDataFrame(
            {
                'Name': ts_curve_names,
                'Date': [None] * len(ts_curve_names),
                'Time': ts_curve_times,
                'Value': ts_curve_values,
                'geometry': [None] * len(ts_curve_names),
            },
            crs=crs,
        )
        gdf_timeseries = pd.concat([gdf_timeseries.copy(deep=True), gdf_timeseries_values.copy(deep=True)])

    # Shape curves
    shape_curve_names = []
    shape_curve_dfs = []
    for shape_curve_name, shape_curve_data in curve_data.items():
        if shape_curve_data['Type'] == 'SHAPE':
            shape_curve_names.append(shape_curve_name)
            df = pd.DataFrame({
                'Depth': shape_curve_data['Depth'],
                'Width': shape_curve_data['Width'],
            })
            shape_curve_dfs.append(df)

            # Store maximum and normalize
            max_depth = df['Depth'].max()
            gdf_conduits.loc[gdf_conduits['Name'] == shape_curve_name[:-3], 'xsec_Geom1'] = max_depth
            gdf_conduits.loc[gdf_conduits['Name'] == shape_curve_name[:-3], 'xsec_Curve'] = shape_curve_name
            df['Width'] = df['Width'] / max_depth
            df['Depth'] = df['Depth'] / max_depth

    if len(shape_curve_names) > 0:
        gdf_shape_curves = create_curves_from_dfs('SHAPE',
                                                  shape_curve_names,
                                                  shape_curve_dfs,
                                                  crs)
    else:
        gdf_shape_curves = None
    feedback.pushInfo(f'Number of shape curves: {len(shape_curve_names)}')

    # Transects
    feedback.pushInfo(f'Number of transects (natural channel geometry): {len(transect_data)}')
    if len(transect_data) > 0:
        gdf_transects, transects_layername = create_section_gdf('Transects', crs)
        gdf_transects.drop(gdf_transects.index, inplace=True)

        gdf_transects_coords, transects_coords_layername = create_section_gdf('Transects_coords', crs)
        gdf_transects_coords.drop(gdf_transects_coords.index, inplace=True)

        gdf_transect_data = pd.DataFrame(
            {
                'Name': transect_data.keys(),
                'Xleft': [x[1]['Xleft'] for x in transect_data.items()],
                'Xright': [x[1]['Xright'] for x in transect_data.items()],
                'Lfactor': [0] * len(transect_data),
                'Wfactor': [0] * len(transect_data),
                'Eoffset': [0] * len(transect_data),
                'Nleft': [x[1]['Nleft'] for x in transect_data.items()],
                'Nright': [x[1]['Nright'] for x in transect_data.items()],
                'Nchanl': [x[1]['Nchanl'] for x in transect_data.items()],
            }
        )
        gdf_transects = pd.concat([gdf_transects, gdf_transect_data])
        gdf_transects['Name'] = gdf_transects['Name'].astype(str).apply(lambda x: sanitize_name(x))

        tcoord_names = []
        tcoord_sta = []
        tcoord_elev = []

        for tname, tcoord_data in transect_data.items():
            for sta, elev in zip(tcoord_data['Stations'], tcoord_data['Elevations']):
                tcoord_names.append(sanitize_name(tname))
                tcoord_sta.append(sta)
                tcoord_elev.append(elev)

        df_tcoord_values = pd.DataFrame(
            {
                'Name': tcoord_names,
                'Elev': tcoord_elev,
                'Station': tcoord_sta,
            }
        )
        gdf_transects_coords = pd.concat([gdf_transects_coords, df_tcoord_values])

        gdf_conduits['xsec_Tsect'] = gdf_conduits['xsec_Tsect'].astype(str).apply(lambda x: sanitize_name(x))

    else:
        gdf_transects = None
        gdf_transects_coords = None
        transects_layername = ''
        transects_coords_layername = ''

    # Inlets
    gdfs_inlets_to_write = []
    if gdf_inlet_info is not None:
        gdf_inlet_usage = xpswmm_2d_capture_to_swmm_gpd(
            gdf_inlet_info,
            'elev',
            'flag',
            'coeff',
            'exponent',
            0,
            crs,
            gdfs_inlets_to_write,
            feedback,
        )
    else:
        gdf_inlet_usage = None

    # Combine sections for inlet curves and shape curves (if they exist)
    curve_dfs = []
    curve_layername = 'Curves--Curves'
    if gdf_shape_curves is not None:
        curve_dfs.append(gdf_shape_curves)
    for gdf, name in gdfs_inlets_to_write:
        if name == curve_layername:
            curve_dfs.append(gdf)
    if len(curve_dfs) > 0:
        gdf_curves = pd.concat(curve_dfs)
    else:
        gdf_curves = None

    # Post-steps
    gdf_junctions, gdf_add_outfalls = downstream_junctions_to_outfalls(
        gdf_junctions,
        gdf_conduits,
        feedback,
    )
    gdf_outfalls = pd.concat([gdf_outfalls, gdf_add_outfalls])

    gdf_inflows = None
    inflows_layername = None
    inflows_nodes = []
    inflows_curves = []
    for ts_name, ts_curve_data in ts_data.items():
        if ts_curve_data['type'] == 'inflow':
            inflows_nodes.append(ts_name.replace('_inflow', ''))
            inflows_curves.append(ts_name)

    if len(inflows_nodes) > 0:
        gdf_inflows_data = gpd.GeoDataFrame(
            {
                'Node': inflows_nodes,
                'Type': ['FLOW']*len(inflows_nodes),
                'Tseries': inflows_curves,
            },
            geometry=[None]*len(inflows_nodes),
            crs=crs,
        )
        gdf_inflows, inflows_layername = create_section_gdf('Inflows', crs)
        gdf_inflows.drop(gdf_inflows.index, inplace=True)
        gdf_inflows = pd.concat([gdf_inflows, gdf_inflows_data])
        gdf_inflows.loc[:, 'geometry'] = gdf_inflows.merge(
            gdf_all_nodes,
            how='left',
            left_on='Node',
            right_on='Name'
        )['geometry_y']

    # print(gdf_junctions)
    # print(gdf_storage)
    # print(gdf_outfalls)
    # print(gdf_conduits)
    # print(gdf_subs)
    # print(gdf_raingages)
    #
    # print(df_options)
    #
    # print(ts_data)
    # print(gdf_timeseries)
    #
    # print(gdf_inlet_info)
    #
    # print(curve_data)
    #
    # print(gdf_transects)

    gdf_junctions.to_file(gpkg_filename, layer=junctions_layername, driver='GPKG', index=False)
    if len(gdf_storage) > 0:
        gdf_storage.to_file(gpkg_filename, layer=storage_layername, driver='GPKG', index=False)
    gdf_outfalls.to_file(gpkg_filename, layer=outfalls_layername, driver='GPKG', index=False)
    gdf_conduits.to_file(gpkg_filename, layer=conduits_layername, driver='GPKG', index=False)

    if len(gdf_subs) > 0:
        gdf_subs.to_file(gpkg_filename, layer=sub_layername, driver='GPKG', index=False)
    gdf_raingages.to_file(gpkg_filename, layer=raingages_layername, driver='GPKG', index=False)
    gdf_timeseries.to_file(gpkg_filename, layer='Curves--Timeseries', driver='GPKG', index=False)
    if len(gdf_title) > 0:
        gdf_title.to_file(gpkg_filename, layer=title_layername, driver='GPKG', index=False)

    gdf_options = gpd.GeoDataFrame(df_options, geometry=[None for i in df_options.index])
    gdf_options.to_file(gpkg_filename, layer='Project--Options', driver='GPKG', index=False)

    for gdf_to_write, layername in gdfs_inlets_to_write:
        if layername == curve_layername:
            continue  # write elsewhere
        gdf_to_write.to_file(gpkg_filename, layer=layername, driver='GPKG', index=False)

    if gdf_curves is not None:
        gdf_curves.to_file(gpkg_filename, layer=curve_layername, driver='GPKG', index=False)

    if gdf_transects is not None:
        gdf_transects.to_file(gpkg_filename, layer=transects_layername, driver='GPKG', index=False)
        gdf_transects_coords.to_file(gpkg_filename, layer=transects_coords_layername, driver='GPKG', index=False)

    if gdf_inflows is not None:
        gdf_inflows.to_file(gpkg_filename, layer=inflows_layername,
                            driver='GPKG', index=False)

    if gdf_inlet_usage is not None:
        gdf_inlet_usage.to_file(iu_filename, layer='inlet_usage', driver='GPKG', index=False)

    swmm_io.write_tuflow_version(gpkg_filename)

    gis_to_swmm(
        gpkg_filename,
        gpkg_filename.with_suffix('.inp'),
        feedback,
    )

    gdf_messages = gpd.GeoDataFrame(
        {
            'Severity': messages_severity,
            'Message': messages_text,
        },
        geometry=messages_location,
        crs=crs,
    )
    gdf_messages.to_file(messages_filename, layer='Messages_with_locations', driver='GPKG', index=False)


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.max_rows', 500)
    pd.set_option('display.width', 200)

    in_filename = Path(
        r'D:\models\TUFLOW\test_models\SWMM\q3\GTModel_2024-05-20\XP Model\GT-SD Alt2b_N Basin_Alt19_Run02\GT-SD '
        r'Alt2b_N Basin_Alt19_Run02.xpx')

    out_filename = Path(
        r'D:\models\TUFLOW\test_models\SWMM\q3\GTModel_2024-05-20\BMT\TUFLOW\model\swmm\gt_from_xp_003.gpkg')
    out_iu_filename = Path(
        r'D:\models\TUFLOW\test_models\SWMM\q3\GTModel_2024-05-20\BMT\TUFLOW\model\swmm\gt_iu_from_xp_003.gpkg')

    messages_filename = Path(
        r'D:\models\TUFLOW\test_models\SWMM\q3\GTModel_2024-05-20\BMT\TUFLOW\model\swmm\gt_from_xp_messages_003.gpkg')

    out_crs = ('PROJCRS["NAD83 / California zone 5",BASEGEOGCRS["NAD83",DATUM["North American Datum 1983",ELLIPSOID['
               '"GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],PRIMEM["Greenwich",0,ANGLEUNIT["degree",'
               '0.0174532925199433]],ID["EPSG",4269]],CONVERSION["unnamed",METHOD["Lambert Conic Conformal (2SP)",'
               'ID["EPSG",9802]],PARAMETER["Latitude of false origin",33.5,ANGLEUNIT["degree",0.0174532925199433],'
               'ID["EPSG",8821]],PARAMETER["Longitude of false origin",-118,ANGLEUNIT["degree",0.0174532925199433],'
               'ID["EPSG",8822]],PARAMETER["Latitude of 1st standard parallel",35.4666666666667,ANGLEUNIT["degree",'
               '0.0174532925199433],ID["EPSG",8823]],PARAMETER["Latitude of 2nd standard parallel",34.0333333333333,'
               'ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8824]],PARAMETER["Easting at false origin",'
               '6561666.66666667,LENGTHUNIT["Foot_US",0.304800609601219],ID["EPSG",8826]],PARAMETER["Northing at '
               'false origin",1640416.66666667,LENGTHUNIT["Foot_US",0.304800609601219],ID["EPSG",8827]]],'
               'CS[Cartesian,2],AXIS["easting",east,ORDER[1],LENGTHUNIT["Foot_US",0.304800609601219]],'
               'AXIS["northing",north,ORDER[2],LENGTHUNIT["Foot_US",0.304800609601219]]]')

    xpx_to_gpkg(in_filename, out_filename, out_iu_filename, messages_filename, out_crs)
