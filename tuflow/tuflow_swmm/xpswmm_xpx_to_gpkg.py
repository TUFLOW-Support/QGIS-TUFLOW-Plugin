from collections import defaultdict
from enum import Enum
import math
from pathlib import Path

import csv
import datetime
import geopandas as gpd
import numpy as np
import pandas as pd
import re
from shapely.geometry import LineString, Polygon

from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.create_bc_connections_gpd import create_bc_connections_gpd
from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf
from tuflow.tuflow_swmm.estry_to_swmm_model import create_curves_from_dfs
from tuflow.tuflow_swmm.fix_multi_link_oulets import extend_multi_link_outfalls_gdf
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.junctions_downstream_to_outfalls import downstream_junctions_to_outfalls
from tuflow.tuflow_swmm.swmm_sanitize import sanitize_name
from tuflow.tuflow_swmm.xpswmm_node2d_convert import xpswmm_2d_capture_to_swmm_gpd
import tuflow.tuflow_swmm.swmm_io as swmm_io
from tuflow.tuflow_swmm.xpswmm_xpx_to_gpkg_tables import get_nearest_height_for_horzellipse, get_arch_width


class SwmmTableEnum(Enum):
    JUNCTIONS = 1
    STORAGE_NODES = 2
    OUTFALLS = 3
    CONDUITS = 4
    SUBCATCHMENTS = 5
    RAINGAGES = 6
    INLETS = 7
    WEIRS = 8
    ORIFICES = 9
    PUMPS = 10


class MultiLinkType(Enum):
    CONDUITS = 1
    PUMPS = 2
    ORIFICES = 3
    WEIRS = 4


def handle_date_time_fields(options_data,
                            options_key_array,
                            options_value_array,
                            feedback,
                            prefix,
                            date_fields):
    date_error = False
    date_obj = None
    for start_date_entry in date_fields:
        if start_date_entry not in options_data:
            feedback.pushWarning(f'Required date entry not found: {start_date_entry}')
            date_error = True
    if not date_error:
        date_obj = datetime.datetime(*[options_data[date_fields[i]] for i in range(5)])
        options_key_array.append(f'{prefix}_DATE')
        options_value_array.append(date_obj.strftime('%m/%d/%Y'))
        options_key_array.append(f'{prefix}_TIME')
        options_value_array.append(date_obj.strftime('%H:%M:%S'))

    return date_obj


def check_for_link_active(re_obj, col1_lower, col2, col5, link_type, multi_links_dict):
    m_cond_num = re_obj.match(col1_lower)
    if m_cond_num is not None:
        num = int(m_cond_num.groups()[0])
        if int(col5) == 1:
            type_number = (link_type, num)
            multi_links_dict[col2][type_number]['active'] = True


#bc_offset_dist,
#bc_offset_width,

def xpx_to_gpkg(xpx_filename, gpkg_filename, bc_offset_dist, bc_offset_width, gis_layers_filename, iu_filename,
                messages_filename, bc_dbase_filename, event_name_default, tef_filename, crs,
                feedback=ScreenProcessingFeedback()) -> dict:
    if isinstance(gpkg_filename, str):
        gpkg_filename = Path(gpkg_filename)

    if isinstance(messages_filename, str):
        messages_filename = Path(messages_filename)

    if isinstance(gis_layers_filename, str):
        gis_layers_filename = Path(gis_layers_filename)

    return_info = {}

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
    links_nums = []
    links_node1 = []
    links_node2 = []
    links_orig_name = []

    vertices = {}
    cur_vertices_name = None
    cur_vertices = []

    subs_name = []
    subs_vertices = {}

    raingages_name = []

    messages_location = []
    messages_severity = []
    messages_text = []

    global_2dlink_settings = {}

    inactive_objects = set()

    # identify multi-links key=link_name, dictionary with key=(type and number) and value = muli-link name
    multi_links = defaultdict(lambda: defaultdict(defaultdict))

    # active for mult-link types
    re_cond_num = re.compile(r'cond(\d)')
    re_weir_num = re.compile(r'weir(\d)')
    re_orifice_num = re.compile(r'orif(\d)')
    re_pump_num = re.compile(r'pump(\d)')

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
                node_names.append(sanitize_name(line_vals[2]))
                node_x.append(float(line_vals[3]))
                node_y.append(float(line_vals[4]))
            elif line_vals_lower[0] == 'link':
                links_name.append(sanitize_name(line_vals[2]))
                links_nums.append(1)
                links_node1.append(sanitize_name(line_vals[3].strip('"')))
                links_node2.append(sanitize_name(line_vals[4].strip('"')))
                links_orig_name.append(sanitize_name(line_vals[2]))
            elif line_vals_lower[0] == 'vertex_start':
                # Don't use vertices for linked cross-sections
                if line_vals_lower[1] != 'link_cs':
                    cur_vertices_name = sanitize_name(line_vals[2])
            # This handles geometry only and puts it into a dict
            elif line_vals_lower[0] == 'catchment':
                sub_name = line_vals[1].strip('"')
                sub_number = int(line_vals[2].strip('"'))
                sub_name = f'{sub_name}#{sub_number}'
                if sub_name not in subs_name:
                    subs_name.append(sub_name)
                pts = []
                npoints = int(line_vals[3])
                for ipoint in range(npoints):
                    nextline = next(xpx_file).strip()
                    nextline_vals = tuple([float(x) for x in nextline.split(' ')])
                    pts.append(nextline_vals)
                subs_vertices[sub_name] = pts
            elif line_vals_lower[0] == 'gldbitem':
                if line_vals_lower[1].strip('"') == 'rainfall':
                    raingages_name.append(sanitize_name(line_vals[2]))
            elif line_vals_lower[0] == 'data':
                check_for_link_active(re_cond_num, line_vals_lower[1], line_vals[2], line_vals[5],
                                      MultiLinkType.CONDUITS, multi_links)
                check_for_link_active(re_weir_num, line_vals_lower[1], line_vals[2], line_vals[5],
                                      MultiLinkType.WEIRS, multi_links)
                check_for_link_active(re_orifice_num, line_vals_lower[1], line_vals[2], line_vals[5],
                                      MultiLinkType.ORIFICES, multi_links)
                check_for_link_active(re_pump_num, line_vals_lower[1], line_vals[2], line_vals[5],
                                      MultiLinkType.PUMPS, multi_links)

                if line_vals_lower[1] == 'r_warea':
                    sub_name = line_vals[2].strip('"')
                    sub_count = int(line_vals[4].strip('"'))
                    areas = [float(x) if x.strip('"') != '' else None for x in line_vals[5:]]
                    for i, area in enumerate(areas):
                        if area is not None and area > 0.0:
                            sub_number = i + 1
                            sub_name_mod = f'{sub_name}#{sub_number}'
                            if sub_name_mod not in subs_name:
                                subs_name.append(sub_name_mod)
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
                    # Multi-link objects sometimes have 0 or 1 in the 3 spot but 0 controls
                    if int(line_vals[3].strip('"')) == 0 and int(line_vals[5].strip('"')) == 0:
                        inactive_objects.add(line_vals[2])
                elif line_vals_lower[1].startswith('cname'):
                    if line_vals_lower[1][5:].strip() != '':
                        type_number = (MultiLinkType.CONDUITS, int(line_vals[1][5:]))
                        multi_links[line_vals[2]][type_number]['name'] = sanitize_name(line_vals[5])
                    else:
                        # Sometimes multi-links get assigned as #1 with only 1 conduit assigned
                        link_name = line_vals[2]
                        if link_name in multi_links:
                            multi_links[link_name][(MultiLinkType.CONDUITS, 1)]['name'] = sanitize_name(line_vals[5])
                elif line_vals_lower[1].startswith('orifname'):
                    type_number = (MultiLinkType.ORIFICES, int(line_vals[3]))
                    multi_links[line_vals[2]][type_number]['name'] = sanitize_name(line_vals[5])
                elif line_vals_lower[1].startswith('weirname'):
                    type_number = (MultiLinkType.WEIRS, int(line_vals[3]))
                    multi_links[line_vals[2]][type_number]['name'] = sanitize_name(line_vals[5])
                elif line_vals_lower[1].startswith('pname'):
                    type_number = (MultiLinkType.PUMPS, int(line_vals[3]))
                    multi_links[line_vals[2]][type_number]['name'] = sanitize_name(line_vals[5])

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
    # This is needed to clear out the information set by copying "gdf_all_nodes"
    gdf_storage['TYPE'] = ''

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

    # Link these later. No need for a message here
    # Linked nodes FLOOD=4 links the node invert to 2D. These are usually connected with HX/SX line in separate layer
    # if len(linked_nodes_sflood4) > 0:
    #     for row in gdf_all_nodes[gdf_all_nodes['Name'].isin(linked_nodes_sflood4)].itertuples(index=False):
    #         messages_location.append(row.geometry)
    #         messages_severity.append('INFO')
    #         messages_text.append(f'Node {row.Name} is linked to 2D at the invert elevation should be connected using '
    #                              f'HX or SX in a 2d_bc layer')

    # Defaults
    if gdf_inlet_info is not None:
        gdf_inlet_info.loc[:, 'ground'] = 0.0
        gdf_inlet_info.loc[:, 'flag'] = 1

    # Handle multi-links
    weir_names = set()
    orifice_names = set()
    pump_names = set()

    for multi_name, multi_dict in multi_links.items():
        # feedback.pushInfo(f'Multi-link name: {multi_name}')
        ilink = links_name.index(multi_name)
        for (link_type, link_num), link_dict in multi_dict.items():
            if 'active' in link_dict and link_dict['active']:
                # The first conduit always comes through outside of the multi_link
                #if link_type == MultiLinkType.CONDUITS and link_num == 1:
                #    continue

                # Sometimes with multilinks the first conduit came through alread (but not always)
                if link_dict['name'] in links_name:
                    continue

                try:
                    # print(link_dict['name'])
                    links_name.append(link_dict['name'])
                    links_nums.append(link_num)
                    links_node1.append(links_node1[ilink])
                    links_node2.append(links_node2[ilink])
                    if link_type == MultiLinkType.WEIRS:
                        weir_names.add(link_dict['name'])
                    elif link_type == MultiLinkType.ORIFICES:
                        orifice_names.add(link_dict['name'])
                    elif link_type == MultiLinkType.PUMPS:
                        pump_names.add(link_dict['name'])
                    if link_num == 1:
                        links_orig_name.append(multi_name)
                    else:
                        links_orig_name.append('')
                except Exception as e:
                    feedback.reportError(
                        f'Error reading multi-link (skipped): {multi_name}\nError: {getattr(e, "message", repr(e))}')

        # del links_name[ilink]
        # del links_node1[ilink]
        # del links_node2[ilink]

    # Build conduits from nodes and vertices
    conduit_geoms = []
    links_to_drop = []
    for link_name, link_num, link_node1, link_node2 in zip(links_name, links_nums, links_node1, links_node2):
        pts = []

        if len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node1, 'geometry']) != 1 or \
                len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node2, 'geometry']) != 1:
            message = ''
            if len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node1, 'geometry']) != 1:
                # Assume we didn't find one but check
                message = f'ERROR - Unable to find node "{link_node1}" for link "{link_name}. Skipping..."'
                if len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node1, 'geometry']) > 1:
                    message = f'ERROR - Found multiple nodes "{link_node1}" for link "{link_name}. Skipping..."'

            if message != '':
                feedback.reportError(message)
                message = ''

            if len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node2, 'geometry']) != 1:
                # Assume we didn't find one but check
                message = f'ERROR - Unable to find node "{link_node2}" for link "{link_name}. Skipping..."'
                if len(gdf_all_nodes.loc[gdf_all_nodes['Name'] == link_node2, 'geometry']) > 1:
                    message = f'ERROR - Found multiple nodes "{link_node2}" for link "{link_name}. Skipping..."'

            if message != '':
                feedback.reportError(message)
            conduit_geoms.append(None)
            links_to_drop.append(link_name)
            continue

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
        conduit_geom = LineString(pts)
        # If the link number is greater than one we want to have extra points to distinguish the links
        if link_num > 1:
            # Make sure we have at least two additional points
            conduit_geom = conduit_geom.segmentize(conduit_geom.length/3.0)
            offset_geom = conduit_geom.offset_curve(conduit_geom.length/20.0*float(link_num))
            # Make sure we have the right number of points
            offset_geom = offset_geom.segmentize(conduit_geom.length/3.0)
            # Make a new geometry with the endpoints of the original with the middle points of the offset geom
            new_points = [conduit_geom.coords[0]] + offset_geom.coords[1:-1] + [conduit_geom.coords[-1]]
            conduit_geom = LineString(new_points)
        conduit_geoms.append(conduit_geom)

    gdf_conduits, conduits_layername = create_section_gdf('Conduits', crs)
    gdf_conduits.drop(gdf_conduits.index, inplace=True)
    gdf_all_links = gpd.GeoDataFrame(
        {
            'Name': links_name,
            'From Node': links_node1,
            'To Node': links_node2,
            'Orig Name': links_orig_name,
        },
        crs=crs,
        geometry=conduit_geoms)
    gdf_conduit_values = gdf_all_links[~gdf_all_links['Name'].isin(weir_names)]
    gdf_conduits = pd.concat([gdf_conduits, gdf_conduit_values])

    gdf_weirs, weirs_layername = create_section_gdf('Weirs', crs)
    gdf_weirs.drop(gdf_weirs.index, inplace=True)
    gdf_weir_values = gdf_all_links[gdf_all_links['Name'].isin(weir_names)]
    gdf_weirs = pd.concat([gdf_weirs, gdf_weir_values])

    gdf_orifices, orifices_layername = create_section_gdf('Orifices', crs)
    gdf_orifices.drop(gdf_orifices.index, inplace=True)
    gdf_orifices_values = gdf_all_links[gdf_all_links['Name'].isin(orifice_names)]
    gdf_orifices = pd.concat([gdf_orifices, gdf_orifices_values])

    gdf_pumps, pumps_layername = create_section_gdf('Pumps', crs)
    gdf_pumps.drop(gdf_pumps.index, inplace=True)
    gdf_pumps_values = gdf_all_links[gdf_all_links['Name'].isin(pump_names)]
    gdf_pumps = pd.concat([gdf_pumps, gdf_pumps_values])

    # Build subcatchments
    subs_geom = []
    for sub_name in subs_name:
        if sub_name in subs_vertices:
            subs_geom.append(Polygon(np.array(subs_vertices[sub_name])))
        else:
            subs_geom.append(None)

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

    gdf_weirs['xsec_XsecType'] = 'RECT_OPEN'
    gdf_weirs['xsec_Geom1'] = 0.0
    gdf_weirs['xsec_Geom2'] = 0.0
    gdf_weirs['xsec_Geom3'] = 0.0
    gdf_weirs['xsec_Geom4'] = 0.0
    gdf_weirs['xsec_Barrels'] = 1
    gdf_weirs['xsec_Tsect'] = ''
    gdf_weirs['Gated'] = 'No'
    gdf_weirs['EC'] = 0
    gdf_weirs['Cd2'] = 0.0
    gdf_weirs['Sur'] = 'Yes'

    gdf_orifices['xsec_Geom1'] = 0.0
    gdf_orifices['xsec_Geom2'] = 0.0
    gdf_orifices['xsec_Geom3'] = 0.0
    gdf_orifices['xsec_Geom4'] = 0.0
    gdf_orifices['xsec_Barrels'] = 1
    gdf_orifices['xsec_Tsect'] = ''

    gdf_pumps['Pcurve'] = '*'

    if len(gdf_subs) > 0:
        gdf_subs['Rain Gage'] = ''
        gdf_subs['Outlet'] = gdf_subs['Name'].str.split('#', n=1, expand=True)[0]
        gdf_subs['Subareas_RouteTo'] = 'OUTLET'
        gdf_subs['CurbLen'] = 0.0
        gdf_subs['SnowPack'] = None  # Name of snowpack item
        gdf_subs.loc[:, ['Infiltration_p1',
                         'Infiltration_p2',
                         'Infiltration_p3',
                         'Infiltration_p4',
                         'Infiltration_p5']] = 0.0
        gdf_subs.loc[:, 'Subareas_Nimp'] = 0.02
        gdf_subs.loc[:, 'Subareas_Nperv'] = 0.05
        gdf_subs.loc[:, ['Subareas_Simp', 'Subareas_Sperv', 'Subareas_PctZero']] = 0.0

        # if we have any null geometries, generate polygons around the outlet
        no_geom_catchment_size = 50.0
        null_sub_geom = gdf_subs['geometry'].isnull()
        outlet_nodes_null_geom = gdf_subs.loc[null_sub_geom, 'Outlet']
        new_geom = outlet_nodes_null_geom.apply(
            lambda x: gdf_all_nodes.loc[
                gdf_all_nodes['Name'] == x, 'geometry'
            ].iloc[0].buffer(no_geom_catchment_size)
        )
        gdf_subs.loc[null_sub_geom, 'geometry'] = new_geom

    gdf_raingages['Form'] = 0
    gdf_raingages['Intvl'] = 1.0
    gdf_raingages['SnowCatchDeficiency'] = 1.0

    swmm_tables = {
        SwmmTableEnum.JUNCTIONS: gdf_junctions,
        SwmmTableEnum.STORAGE_NODES: gdf_storage,
        SwmmTableEnum.OUTFALLS: gdf_outfalls,
        SwmmTableEnum.CONDUITS: gdf_conduits,
        SwmmTableEnum.SUBCATCHMENTS: gdf_subs,
        SwmmTableEnum.RAINGAGES: gdf_raingages,
        SwmmTableEnum.INLETS: gdf_inlet_info,
        SwmmTableEnum.WEIRS: gdf_weirs,
        SwmmTableEnum.ORIFICES: gdf_orifices,
        SwmmTableEnum.PUMPS: gdf_pumps,
    }

    feedback.pushInfo(f'Number of nodes: {len(node_names)}')
    feedback.pushInfo(f'  Number of junctions: {len(gdf_junctions)}')
    feedback.pushInfo(f'  Number of storage nodes: {len(gdf_storage)}')
    feedback.pushInfo(f'  Number of outfalls: {len(gdf_outfalls)}')
    feedback.pushInfo(f'Number of links: {len(links_name)}')
    feedback.pushInfo(f'Number of Subcatchments: {len(subs_name)}')

    # Make sure we have nodes and links
    if len(node_names) == 0 or len(links_name) == 0:
        object_text = 'nodes'
        if len(node_names) == 0 and len(links_name) == 0:
            object_text = 'nodes and links'
        if len(links_name) == 0:
            object_text = 'links'
        feedback.reportError(f'No {object_text} found in the file. Check that the model is complete and that all '
                             f'objects were exported to xpx.', fatalError=True)
        return return_info

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
        [('data', 'cntls'), SwmmTableEnum.STORAGE_NODES, 'TYPE', 2, str, 5],
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
        # The line below didn't work consistently for multi-link objects
        # [('data', 'locmode'), SwmmTableEnum.CONDUITS, 'Active', 2, int, 5],

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

        # Weirs
        [('data', 'coeff'), SwmmTableEnum.WEIRS, 'Cd', 2, float, 5],
        [('data', 'kweir'), SwmmTableEnum.WEIRS, 'Type', 2, str, 5],
        [('data', 'ycrest'), SwmmTableEnum.WEIRS, 'CrestHt', 2, float, 5],
        [('data', 'wlen'), SwmmTableEnum.WEIRS, 'xsec_Geom2', 2, float, 5],
        [('data', 'ytop'), SwmmTableEnum.WEIRS, 'xsec_Geom1', 2, float, 5],

        # Orifices
        [('data', 'onklass'), SwmmTableEnum.ORIFICES, 'Type', 2, str, 5],
        [('data', 'corif'), SwmmTableEnum.ORIFICES, 'Qcoeff', 2, float, 5],
        [('data', 'zp'), SwmmTableEnum.ORIFICES, 'Offset', 2, float, 5],
        [('data', 'aorif'), SwmmTableEnum.ORIFICES, 'xsec_Geom1', 2, float, 5],
        [('data', 'dorif'), SwmmTableEnum.ORIFICES, 'xsec_Geom2', 2, float, 5],
        [('data', 'isqrnd'), SwmmTableEnum.ORIFICES, 'xsec_XsecType', 2, str, 5],

        # Subcatchments
        [('data', 'r_rainsel'), SwmmTableEnum.SUBCATCHMENTS, 'Rain Gage', 2, str, 5],
        [('data', 'r_warea'), SwmmTableEnum.SUBCATCHMENTS, 'Area', 2, float, 5],
        [('data', 'r_wimp'), SwmmTableEnum.SUBCATCHMENTS, 'PctImperv', 2, float, 5],
        [('data', 'r_width'), SwmmTableEnum.SUBCATCHMENTS, 'Width', 2, float, 5],
        [('data', 'r_wslope'), SwmmTableEnum.SUBCATCHMENTS, 'PctSlope', 2, float, 5],
        [('data', 'r_infilsel'), SwmmTableEnum.SUBCATCHMENTS, 'Tag', 2, str, 5],  # Temporarily store infiltration type
        [('data', 'r_cn'), SwmmTableEnum.SUBCATCHMENTS, 'Infiltration_p1', 2, float, 5],

        # Raingages
        [('gldbdata', 'r_thisto', 'rainfall'), SwmmTableEnum.RAINGAGES, 'Intvl', 3, float, 5],
        [('gldbdata', 'r_kprepc', 'rainfall'), SwmmTableEnum.RAINGAGES, 'Form', 3, str, 5],
        [('gldbdata', 'r_ktimec', 'rainfall'), SwmmTableEnum.RAINGAGES, 'IntvlType', 3, int, 5],
        [('gldbdata', 'r_ktimev', 'rainfall'), SwmmTableEnum.RAINGAGES, 'IntvlType', 3, int, 5],
        [('gldbdata', 'r_ktype', 'rainfall'), SwmmTableEnum.RAINGAGES, 'TimeType', 3, int, 5],

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
                try:
                    swmm_tables[entry_type][entry_col] = swmm_tables[entry_type][entry_col].astype(entry_val_type)
                except Exception as e:
                    swmm_tables[entry_type][entry_col] = None
                    feedback.reportError(
                        f'Error converting data for {headings}. Error: {getattr(e, "message", repr(e))}')
        else:
            swmm_tables[entry_type][entry_col] = entry_val_type() if entry_val_type in [str, float, int] else \
                entry_val_type(None)

    # curve data
    curve_data = defaultdict(dict)
    transect_data = defaultdict(dict)
    ts_data = defaultdict(dict)

    global_storm_data = defaultdict(list)  # store lists of attributes to make a dataframe

    # infiltration data
    infiltration_methods = {
        0: 'HORTON',
        1: 'GREEN_AMPT',
        3: 'CURVE_NUMBER',
    }
    unsupported_infiltration_encountered = False
    infiltration_data = defaultdict(dict)

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
    subareas_entries = [
        # use infiltration data above
        # [('gldbdata', 'r_suct', 'infiltration'), 'Infiltration_p1', 3, float, 5],
        # [('gldbdata', 'r_hydcon', 'infiltration'), 'Infiltration_p2', 3, float, 5],
        # [('gldbdata', 'r_smdmax', 'infiltration'), 'Infiltration_p3', 3, float, 5],
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
                    item_name = sanitize_name(line_vals[entry_name_col])
                    # for subcatchments we always need the number
                    if entry_type == SwmmTableEnum.SUBCATCHMENTS:
                        item_name = f'{item_name}#{int(line_vals[3]) + 1}'
                    elif entry_type == SwmmTableEnum.CONDUITS:
                        if item_name in multi_links:
                            link_num = int(line_vals[3])
                            if (MultiLinkType.CONDUITS, link_num) in multi_links[item_name]:
                                item_name = multi_links[item_name][(MultiLinkType.CONDUITS, link_num)]['name']
                    elif entry_type == SwmmTableEnum.WEIRS:
                        if item_name in multi_links:
                            link_num = int(line_vals[3])
                            if (MultiLinkType.WEIRS, link_num) in multi_links[item_name]:
                                item_name = multi_links[item_name][(MultiLinkType.WEIRS, link_num)]['name']
                    elif entry_type == SwmmTableEnum.ORIFICES:
                        if item_name in multi_links:
                            link_num = int(line_vals[3])
                            if (MultiLinkType.ORIFICES, link_num) in multi_links[item_name]:
                                item_name = multi_links[item_name][(MultiLinkType.ORIFICES, link_num)]['name']
                    elif entry_type == SwmmTableEnum.PUMPS:
                        if item_name in multi_links:
                            link_num = int(line_vals[3])
                            if (MultiLinkType.PUMPS, link_num) in multi_links[item_name]:
                                item_name = multi_links[item_name][(MultiLinkType.PUMPS, link_num)]['name']

                    item_val = entry_val_type(line_vals[entry_val_col])
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
                ts_name = sanitize_name(line_vals[3])
                ts_data[ts_name]['type'] = 'rainfall'
                ts_values = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['values'] = ts_values
            elif line_vals_lower[0] == 'gldbdata' and line_vals_lower[1] == 'r_rmult' \
                    and line_vals_lower[2] == 'rainfall':
                ts_name = sanitize_name(line_vals[3])
                ts_data[ts_name]['multiplier'] = float(line_vals[5])
            elif line_vals_lower[0] == 'gldbdata' and line_vals_lower[1] == 'r_rain' \
                    and line_vals_lower[2] == 'rainfall':
                ts_name = sanitize_name(line_vals[3])
                ts_data[ts_name]['type'] = 'rainfall'
                ts_values = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['values'] = ts_values

            # inflows
            if line_vals_lower[0] == 'data' and line_vals_lower[1] == 'teo':
                ts_name = sanitize_name(line_vals[2]) + '_inflow'
                ts_times = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['type'] = 'inflow'
                ts_data[ts_name]['times'] = ts_times
            elif line_vals_lower[0] == 'data' and line_vals_lower[1] == 'qcard':
                ts_name = sanitize_name(line_vals[2]) + '_inflow'
                ts_values = [float(x) for x in line_vals[5:]]
                ts_data[ts_name]['values'] = ts_values

            # transects
            transect_fields_lc = ['el', 'sta', 'nsgd_stchr', 'nsgd_stchl', 'nsgd_xnch', 'nsgd_xnr', 'nsgd_xnl']
            if line_vals_lower[0] == 'gldbdata':
                if line_vals_lower[1] in transect_fields_lc and line_vals_lower[2].strip(
                        '"') == 'natural section shape':
                    transect_name = sanitize_name(line_vals[3])
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
                curve_name = sanitize_name(line_vals[2]) + '_hw'
                curve_x = [float(x) for x in line_vals[5:]]
                curve_data[curve_name]['Type'] = 'SHAPE'
                curve_data[curve_name]['Depth'] = curve_x
            elif line_vals_lower[0] == 'data' and line_vals_lower[1] == 'sw':
                curve_name = sanitize_name(line_vals[2]) + '_hw'
                curve_y = [float(x) for x in line_vals[5:]]
                curve_data[curve_name]['Width'] = curve_y

            # Read and apply subarea parameters
            for headings, entry_col, entry_name_col, entry_val_type, entry_val_col in subareas_entries:
                matches = True
                for icol, heading in enumerate(headings):
                    if len(line_vals) < icol + 1:
                        matches = False
                        break
                    elif line_vals_lower[icol] != heading:
                        matches = False
                        break
                if matches:
                    item_name = sanitize_name(line_vals[entry_name_col])
                    item_val = entry_val_type(line_vals[entry_val_col])
                    gdf_subs.loc[gdf_subs['Tag'] == item_name, entry_col] = item_val

            # global storm data
            if line_vals_lower[0] == 'global_storm':
                active = int(line_vals[2]) == 1
                name = sanitize_name(line_vals[3])
                return_interval = float(line_vals[5])
                rainfall = sanitize_name(line_vals[6])
                if line_vals[7] is None or line_vals[7] == '':
                    override_multiplier = False
                    multiplier = 1.0
                else:
                    override_multiplier = int(line_vals[7]) == 1
                    multiplier = float(line_vals[8])

                global_storm_data['Active'].append(active)
                global_storm_data['Name'].append(name)
                global_storm_data['ReturnInterval'].append(return_interval)
                global_storm_data['Rainfall'].append(rainfall)
                global_storm_data['OverrideMultiplier'].append(override_multiplier)
                global_storm_data['Multiplier'].append(multiplier)

            # Infiltration data
            if line_vals_lower[0] == 'gldbdata':
                if line_vals_lower[1] == 'r_infilm' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    infiltration_number = int(line_vals[5])
                    if infiltration_number in infiltration_methods:
                        infiltration_method = infiltration_methods[infiltration_number]
                    else:
                        unsupported_infiltration_encountered = True
                        infiltration_method = 'GREEN_AMPT'
                    infiltration_data[infiltration_name]['Type'] = infiltration_method
                if line_vals_lower[1] == 'scs_cn' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    curve_number = float(line_vals[5])
                    infiltration_data[infiltration_name]['CURVE_NUMBER_p1'] = curve_number
                elif line_vals_lower[1] == 'r_wlmax' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    max_infil_rate = float(line_vals[5])
                    infiltration_data[infiltration_name]['HORTON_p1'] = max_infil_rate
                elif line_vals_lower[1] == 'r_wlmin' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    min_infil_rate = float(line_vals[5])
                    infiltration_data[infiltration_name]['HORTON_p2'] = min_infil_rate
                elif line_vals_lower[1] == 'r_decay' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    decay_rate = float(line_vals[5]) * 3600.0
                    infiltration_data[infiltration_name]['HORTON_p3'] = decay_rate
                elif line_vals_lower[1] == 'r_maxinf' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    max_infil = float(line_vals[5])
                    infiltration_data[infiltration_name]['HORTON_p5'] = max_infil
                elif line_vals_lower[1] == 'r_suct' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    cap_suction = float(line_vals[5])
                    infiltration_data[infiltration_name]['GREEN_AMPT_p1'] = cap_suction
                elif line_vals_lower[1] == 'r_hydcon' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    hyd_connectivity = float(line_vals[5])
                    infiltration_data[infiltration_name]['GREEN_AMPT_p2'] = hyd_connectivity
                elif line_vals_lower[1] == 'r_smdmax' and line_vals_lower[2] == 'infiltration':
                    infiltration_name = line_vals[3]
                    init_deficit = float(line_vals[5])
                    infiltration_data[infiltration_name]['GREEN_AMPT_p3'] = init_deficit

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

    gdf_outfalls['Type'] = gdf_outfalls['Type'].apply(lambda x:
                                                      xpx_ntide_to_swmm_outfall[
                                                          x] if x in xpx_ntide_to_swmm_outfall else None)
    if sum(gdf_outfalls['Type'].isnull()) > 0:
        feedback.pushWarning('Not all outfall types converted and must be filled in manually.')

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
                    feedback.reportError('Inactive nodes encountered which will be ignored.')
                    inactive_node_message_given = True

                # Add information for the messages file
                for row in gdf_inactive_nodes[['Name', 'geometry']].itertuples():
                    messages_location.append(row.geometry)
                    messages_severity.append('WARNING')
                    messages_text.append(f'Inactive node {row.Name} ignored.')

            node_table.drop(node_table[node_table['Name'].isin(inactive_objects)].index, inplace=True)

    # drop inactive nodes from the all_nodes table (warning already given)
    gdf_all_nodes = gdf_all_nodes[~gdf_all_nodes['Name'].isin(inactive_objects)]

    # Remove inactive conduits
    # feedback.pushInfo('\n'.join(sorted(inactive_objects)))
    inactive_conduits = gdf_conduits['Orig Name'].isin(inactive_objects)
    gdf_inactive_conduits = gdf_conduits[inactive_conduits].copy(deep=True)

    if len(gdf_inactive_conduits) > 0:
        feedback.reportError(
            'Inactive conduits encountered which will be ignored. To convert these conduits first active them in '
            'XPSWMM.')

        # Add information for the messages file
        for row in gdf_inactive_conduits[['Name', 'geometry']].itertuples():
            messages_location.append(row.geometry.centroid)
            messages_severity.append('WARNING')
            messages_text.append(f'Inactive conduit {row.Name} ignored.')

    gdf_conduits = gdf_conduits[~inactive_conduits].copy(deep=True)

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

    xpx_to_swmm_weir = {
        '1': 'TRANSVERSE',
        '3': 'SIDEFLOW'
    }
    if len(gdf_weirs) > 0:
        gdf_weirs.loc[:, 'Type'] = gdf_weirs.loc[:, 'Type'].apply(lambda x: xpx_to_swmm_weir[x])

    xpx_to_swmm_orifice_type = {
        '1': 'SIDE',
        '2': 'BOTTOM',
    }

    xpx_to_swmm_orifice_shape = {
        '0': 'CIRCULAR',
        '1': 'RECT_CLOSED',
    }

    if len(gdf_orifices) > 0:
        gdf_orifices.loc[:, 'Type'] = gdf_orifices.loc[:, 'Type'].apply(lambda x: xpx_to_swmm_orifice_type[x])

        gdf_orifices.loc[:, 'xsec_XsecType'] = gdf_orifices.loc[:, 'xsec_XsecType'].apply(lambda x:
                                                                                          xpx_to_swmm_orifice_shape[x])

        # Geom1 is area and Geom2 is height convert to diameter (circular) or height,width
        gdf_orifices.loc[
            gdf_orifices['xsec_XsecType'] == 'CIRCULAR',
            'xsec_Geom1'
        ] = np.sqrt(gdf_orifices.loc[
                        gdf_orifices['xsec_XsecType'] == 'CIRCULAR',
                        'xsec_Geom1'
                    ] / math.pi)

        rect_heights = gdf_orifices.loc[
            gdf_orifices['xsec_XsecType'] == 'RECT_CLOSED',
            'xsec_Geom2'
        ]
        rect_widths = gdf_orifices.loc[
                          gdf_orifices['xsec_XsecType'] == 'RECT_CLOSED',
                          'xsec_Geom1'
                      ] / rect_heights
        gdf_orifices.loc[
            gdf_orifices['xsec_XsecType'] == 'RECT_CLOSED',
            ['xsec_Geom1']
        ] = rect_heights
        gdf_orifices.loc[
            gdf_orifices['xsec_XsecType'] == 'RECT_CLOSED',
            ['xsec_Geom2']
        ] = rect_widths

    # We do not currently transfer pump information
    if len(gdf_pumps) > 0:
        feedback.reportError(
            'Pumps encountered and pump attributes not currently coonverted. See messages file for locations '
            'and add attributes manually.')

        # Add information for the messages file
        for row in gdf_pumps[['Name', 'geometry']].itertuples():
            if row.geometry is None:
                feedback.pushWarning(f'\nPump {row.Name} has null geometry which must be manually fixed.\n')
                continue
            messages_location.append(row.geometry.centroid)
            messages_severity.append('ERROR')
            messages_text.append(f'Pump attributes not converted {row.Name}.')

    # Handle ellipses
    using_metric_units = 'metric' in options_data and options_data['metric'] == 1

    # horizontal ellipses are flipped
    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom2'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom1']
    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom1'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'HORIZ_ELLIPSE', 'xsec_Geom2'].apply(
            lambda x: get_nearest_height_for_horzellipse(using_metric_units, x)
        )

    gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'VERT_ELLIPSE', 'xsec_Geom2'] = \
        gdf_conduits.loc[gdf_conduits['xsec_XsecType'] == 'VERT_ELLIPSE', 'xsec_Geom1'].apply(
            lambda x: get_nearest_height_for_horzellipse(using_metric_units, x)
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
            'Modified-basket handle geometry encountered without a width assigned. Please review these conduits and '
            'assign appropriate widths.')

        # Add information for the messages file
        for row in gdf_modbasket_nowidth[['geometry', 'Name']].itertuples():
            messages_location.append(row.geometry.centroid)
            messages_severity.append('ERROR')
            messages_text.append(f'The width for modified basket handle conduit {row.Name} was not written to the '
                                 f'file and must be filled in manually.')

    # subcatchments
    gdf_subs['PctSlope'] = gdf_subs['PctSlope'] * 100.0
    # infiltration
    subs_infiltration = ~gdf_subs['Tag'].isnull()
    subs_tags = gdf_subs.loc[subs_infiltration, 'Tag']
    gdf_subs.loc[subs_infiltration, 'Infiltration_Method'] = subs_tags.apply(
        lambda x: infiltration_data[x]['Type'] if x in infiltration_data and
                                                  'Type' in infiltration_data[x] else None
    )
    for infil_pn in range(1, 6):
        gdf_subs.loc[subs_infiltration, f'Infiltration_p{infil_pn}'] = gdf_subs[subs_infiltration].apply(
            lambda x: infiltration_data[x['Tag']][f'{x["Infiltration_Method"]}_p{infil_pn}'] if
            x['Tag'] in infiltration_data and
            f'{x["Infiltration_Method"]}_p{infil_pn}' in
            infiltration_data[
                x['Tag']] else 0,
            axis=1
        )

    infiltration_type = 'GREEN_AMPT'
    infil_types = gdf_subs.loc[subs_infiltration, 'Infiltration_Method'].unique()
    if len(infil_types) == 1:
        infiltration_type = infil_types[0]

    if len(gdf_subs[gdf_subs['Infiltration_Method'] == 'CURVE_NUMBER']):
        feedback.pushWarning('Subcatchments use the CURVE_NUMBER method. XPSWMM does not provide a value for required '
                             'parameter 3 (dry time in days)')
    if len(gdf_subs[gdf_subs['Infiltration_Method'] == 'HORTON']):
        feedback.pushWarning('Subcatchments use the HORTON method. XPSWMM does not provide a value for required '
                             'parameter 4 (dry time in days)')
    if unsupported_infiltration_encountered:
        feedback.reportError(
            'Infiltration options were encountered that used unsupported infiltration method. These were defaulted to '
            'GREEN_AMPT.')
    gdf_subs['Tag'] = None

    raingages_intvl_minutes = gdf_raingages['IntvlType'] == 0
    gdf_raingages.loc[raingages_intvl_minutes, 'Intvl'] = (
            gdf_raingages.loc[raingages_intvl_minutes, 'Intvl'] / 60.0)
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
    start_datetime = handle_date_time_fields(options_data,
                                             options_key_array,
                                             options_value_array,
                                             feedback,
                                             'START',
                                             start_fields)

    end_fields = ['end_year', 'end_month', 'end_day', 'end_hour', 'end_minute', 'end_second']
    end_datetime = handle_date_time_fields(options_data,
                                           options_key_array,
                                           options_value_array,
                                           feedback,
                                           'END',
                                           end_fields)

    options_key_array.append('REPORT_STEP')
    if 'output_frequency' in options_data:
        output_freq_s = math.floor(options_data['output_frequency'])
    else:
        output_freq_s = 300
        feedback.pushWarning('No output interval set. Defaulting to 5 minutes.')
    hours = output_freq_s // 3600
    minutes = (output_freq_s - hours * 3600) // 60
    seconds = (output_freq_s - hours * 3600) % 60
    options_value_array.append(f'{hours:02}:{minutes:02}:{seconds:02}')

    return_info['start_date'] = start_datetime
    return_info['end_date'] = end_datetime

    if 'metric' in options_data and options_data['metric'] == 1:
        options_key_array.append('FLOW_UNITS')
        options_value_array.append('CMS')
    else:
        options_key_array.append('FLOW_UNITS')
        options_value_array.append('CFS')

    options_key_array.append('INFILTRATION')
    options_value_array.append(infiltration_type)
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

    # Handle global storms
    df_global_storms = pd.DataFrame(global_storm_data)

    # Hanle time-series curves
    ts_curve_names = []
    ts_curve_times = []
    ts_curve_values = []
    for ts_name, ts_curve_data in ts_data.items():
        # feedback.pushInfo(ts_curve_data['type'])
        if ts_curve_data['type'] == 'inflow':
            times = np.array(ts_curve_data['times'])
        else:  # rainfall data
            fixed_rainfall_timestep = True
            # fixed_rainfall_timestep = gdf_raingages.loc[gdf_raingages['Name'] == ts_name, 'TimeType'].iloc[0] == 0
            if fixed_rainfall_timestep:
                interval = gdf_raingages.loc[gdf_raingages['Name'] == ts_name, 'Intvl'].iloc[0]
                times = np.array(range(0, len(ts_curve_data['values']) + 1)).astype(float) * interval
                # feedback.pushInfo(
                #    f'Num values: {len(ts_curve_data['values'])}   Num times: {len(times)}   interval: {interval}')
            else:
                times = ts_curve_data['times']

        values = np.array(ts_curve_data['values'])
        if ts_curve_data['type'] == 'rainfall':
            # add a 0 at the end
            ts_name_orig = ts_name
            ts_name = ts_name + '_rf'
            values = np.append(values, np.array([0.0]), axis=0)

            # if it is intensity and the interval is minutes multiply by 60.0
            raingage_in_minutes = int(
                gdf_raingages.loc[gdf_raingages['Name'] == ts_name_orig, 'IntvlType'].iloc[0]) == 0
            is_intensity = gdf_raingages.loc[gdf_raingages['Name'] == ts_name_orig, 'Form'].iloc[
                               0].lower() == 'intensity'
            if is_intensity and raingage_in_minutes:
                if 'multilplier' in ts_curve_data:
                    ts_curve_data['multiplier'] = ts_curve_data['multiplier'] * 60.0
                else:
                    ts_curve_data['multiplier'] = 60.0

        if 'multiplier' in ts_curve_data:
            values *= ts_curve_data['multiplier']

        # feedback.pushInfo(f'Curve: {ts_name}')
        # feedback.pushInfo(f'Number curve times: {len(times)}')
        # feedback.pushInfo((f'Number curve values: {len(values)}'))

        ts_curve_names = ts_curve_names + [ts_name] * len(times)
        ts_curve_times = ts_curve_times + list(times)
        ts_curve_values = ts_curve_values + list(values)

    # feedback.pushInfo(f'Number curve names: {len(ts_curve_names)}')
    # feedback.pushInfo(f'Number curve times: {len(ts_curve_times)}')
    # feedback.pushInfo((f'Number curve values: {len(ts_curve_values)}'))
    if ts_curve_names:
        gdf_timeseries_values = gpd.GeoDataFrame(
            {
                'Name': ts_curve_names,
                'Date': [''] * len(ts_curve_names),
                'Time': ts_curve_times,
                'Value': ts_curve_values,
                'geometry': [None] * len(ts_curve_names),
            },
            crs=crs,
        )
        # gdf_timeseries = pd.concat([gdf_timeseries.copy(deep=True), gdf_timeseries_values.copy(deep=True)])
        for col in gdf_timeseries:
            if col not in gdf_timeseries_values.columns:
                gdf_timeseries_values[col] = ''
        gdf_timeseries = gdf_timeseries_values[gdf_timeseries.columns]

    # If we have a custom conduit that doesn't have a curve filled but has a xsec_Tsect column then it should be
    # irregular
    custom_culverts_null_curve = ((gdf_conduits['xsec_XsecType'] == 'CUSTOM') &
                                  (gdf_conduits['xsec_Curve'].isnull()) &
                                  (~gdf_conduits['xsec_Tsect'].isnull()) &
                                  (gdf_conduits['xsec_Tsect'] != ''))
    gdf_conduits.loc[custom_culverts_null_curve, 'xsec_XsecType'] = 'IRREGULAR'

    # if the custom conduit still doesn't have a curve use the conduit's original name with "_hw"
    # It appears that XPSWMM will not write the curve if it matches the name
    # custom_culverts_null_curve = (gdf_conduits['xsec_XsecType'] == 'CUSTOM') & (gdf_conduits['xsec_Curve'].isnull())
    # gdf_conduits.loc[custom_culverts_null_curve, 'xsec_Curve'] = gdf_conduits.loc[
    #    custom_culverts_null_curve, 'Orig Name'] + '_hw'

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

            # Sometimes with multiple pipes this is needed because XPSWMM uses the name within the multi-link for the
            # conduit but the shape curve name
            gdf_conduits.loc[gdf_conduits['Orig Name'] == shape_curve_name[:-3], 'xsec_Geom1'] = max_depth
            gdf_conduits.loc[gdf_conduits['Orig Name'] == shape_curve_name[:-3], 'xsec_Curve'] = shape_curve_name

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

    # Drop conduits that do not have a length. Sometimes XPSWMM writes out a partial multi-link even though it is not
    # a multi-link channel. This creates incomplete channels that must be removed.
    gdf_conduits = gdf_conduits.dropna(subset='Length')

    gdf_junctions, gdf_add_outfalls = downstream_junctions_to_outfalls(
        gdf_junctions,
        gdf_conduits,
        feedback,
    )
    gdf_outfalls = pd.concat([gdf_outfalls, gdf_add_outfalls])

    # Fix multiple links to a single outfall (not supported by SWMM)
    # Dummy conduits will give the same result
    outfall_changes, gdf_junctions, gdf_outfalls, gdf_conduits = extend_multi_link_outfalls_gdf(
        gdf_all_links,
        gdf_outfalls,
        gdf_junctions,
        gdf_conduits,
        1.0,
        feedback,
    )
    # Move connections to new extension
    for old_outfall, new_outfall in outfall_changes.items():
        if old_outfall in linked_nodes_sflood4:
            linked_nodes_sflood4.remove(old_outfall)
            linked_nodes_sflood4.add(new_outfall)

    # Inlets
    gdfs_inlets_to_write = []
    if gdf_inlet_info is not None:
        # drop inlets if not snapped to a valid node (removed by inactive)
        gdf_inlet_info = gdf_inlet_info[gdf_inlet_info['Name'].isin(gdf_all_nodes['Name'])]

        # if inlets are snapped to outlets convert to linked_nodes_sflood4 - connected to 2D at a node
        dropped_inlet_names = gdf_inlet_info.loc[gdf_inlet_info['Name'].isin(gdf_outfalls['Name']), 'Name']
        feedback.pushWarning(
            f'Inlets improperly connected to an outlet were converted to SX connections: {", ".join(dropped_inlet_names)}')
        gdf_inlet_info = gdf_inlet_info[~gdf_inlet_info['Name'].isin(gdf_outfalls['Name'])]
        linked_nodes_sflood4 = linked_nodes_sflood4 | set(dropped_inlet_names)

        # Set defaults coeff and exponent if flag is set and they are null or na
        inlets = gdf_inlet_info['flag']
        null_coeff = ~gdf_inlet_info['coeff'].apply(np.isfinite)
        null_exponent = ~gdf_inlet_info['exponent'].apply(np.isfinite)

        if len(gdf_inlet_info.loc[inlets & null_coeff]) > 0:
            feedback.pushWarning(
                'Invalid inlet capture coefficients encountered. Using 1.0. See messages file for locations.')
            for row in gdf_inlet_info[inlets & null_coeff].itertuples(index=False):
                messages_location.append(row.geometry)
                messages_severity.append('WARNING')
                messages_text.append(
                    f'Inlet has invalid capture coefficient: {row.coeff}. A default value of 1.0 will be used.'
                )
            gdf_inlet_info.loc[inlets & null_coeff, 'coeff'] = 1.0

        if len(gdf_inlet_info.loc[inlets & null_exponent]) > 0:
            feedback.pushWarning(
                'Invalid inlet capture exponents encountered. Using 0.0. See messages file for locations.')
            for row in gdf_inlet_info[inlets & null_exponent].itertuples(index=False):
                messages_location.append(row.geometry)
                messages_severity.append('WARNING')
                messages_text.append(
                    f'Inlet has invalid capture exponent: {row.exponent}. A default value of 1.0 will be used.'
                )
            gdf_inlet_info.loc[inlets & null_exponent, 'exponent'] = 1.0

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


    # Add new conduits to all links
    new_conduits = ~gdf_conduits['Name'].isin(gdf_all_links['Name'])
    # print(new_conduits)
    gdf_all_links_new_conduits = gdf_conduits[new_conduits][['Name', 'From Node', 'To Node', 'geometry']]
    gdf_all_links_new_conduits['Orig Name'] = gdf_all_links_new_conduits['Name']
    gdf_all_links = pd.concat([
        gdf_all_links,
        gdf_all_links_new_conduits,
    ], axis=0, ignore_index=True)



    # Do boundary condition HX/SX connections to nodes connected at inverts
    # Use polylines because they are required for junction and storage nodes

    bc_set_z_flag = True
    if len(linked_nodes_sflood4) > 0:
        # print(f'\nLinked nodes ({len(linked_nodes_sflood4)})')
        # print(linked_nodes_sflood4)

        gdf_outfalls_conn = gdf_outfalls[gdf_outfalls['Name'].isin(linked_nodes_sflood4)]
        # print(f'\nLinked outfalls ({len(gdf_outfalls_conn)})')
        # print(gdf_outfalls_conn)

        gdf_junction_conn = gdf_junctions[gdf_junctions['Name'].isin(linked_nodes_sflood4)]
        # print(f'\nLinked junctions ({len(gdf_junction_conn)})')
        # print(gdf_junction_conn)

        # print('\nLinked storage')
        gdf_storage_conn = gdf_storage[gdf_storage['Name'].isin(linked_nodes_sflood4)]
        # print(gdf_storage_conn)

        # print('\nAll links')
        # print(gdf_all_links)

        gdfs_bc_conn = []
        if len(gdf_outfalls_conn) > 0:
            gdf_bc_outfalls = create_bc_connections_gpd(
                gdf_all_links,
                gdf_outfalls_conn,
                True,
                bc_offset_dist,
                bc_offset_width,
                bc_set_z_flag,
                feedback,
            )
            gdfs_bc_conn.append(gdf_bc_outfalls)

        if len(gdf_junction_conn) > 0:
            gdf_bc_junctions = create_bc_connections_gpd(
                gdf_all_links,
                gdf_junction_conn,
                False,
                bc_offset_dist,
                bc_offset_width,
                bc_set_z_flag,
                feedback,
            )
            gdfs_bc_conn.append(gdf_bc_junctions)

        if len(gdf_storage_conn) > 0:
            gdf_bc_storage = create_bc_connections_gpd(
                gdf_all_links,
                gdf_storage_conn,
                False,
                bc_offset_dist,
                bc_offset_width,
                bc_set_z_flag,
                feedback,
            )
            gdfs_bc_conn.append(gdf_bc_storage)

        gdf_bc_conn = pd.concat(gdfs_bc_conn)
        gdf_bc_conn.to_file(gis_layers_filename,
                            layer='2d_bc_swmm_connections',
                            driver='GPKG')

        # test_gpkg_filename = Path(r'C:\TUFLOW\Dev\TUFLOW\qgis_plugin\tuflow\test\swmm\input') / 'xpx_create_bc_connections.gpkg'
        # gdf_all_links.to_file(test_gpkg_filename, layer='All Links', driver='GPKG', index=False)
        # gdf_outfalls_conn.to_file(test_gpkg_filename, layer='Outfalls', driver='GPKG', index=False)
        # gdf_junction_conn.to_file(test_gpkg_filename, layer='Junctions', driver='GPKG', index=False)

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
                'Type': ['FLOW'] * len(inflows_nodes),
                'Tseries': inflows_curves,
            },
            geometry=[None] * len(inflows_nodes),
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

    # Multi-link conduits will appear on top of each other (link to same nodes). Modify the geometries so they can be
    # differentiated- handled above
    # gdf_duplicate_links = gdf_all_links[gdf_all_links[['From Node', 'To Node']].duplicated() == True]
    # print(gdf_duplicate_links)

    # Handle BC database, curves, and TEF file
    # Sometimes XPSWMM writes multiple versions of the same raingage which SWMM doesn't like make them unique
    gdf_raingages = gdf_raingages.drop_duplicates(subset=['Name'])
    if len(global_storm_data) > 0:
        # If we are using global storms, rain gage is always rainfall and set using events
        gdf_raingages['Intvl'] = gdf_raingages['Intvl'].min()
        gdf_raingages = gdf_raingages.drop(gdf_raingages.index[1:])
        gdf_raingages['Name'] = 'Rainfall'
        gdf_raingages['Tseries'] = 'Rainfall'

        gdf_subs['Rain Gage'] = 'Rainfall'

        df_bc_dbase = pd.DataFrame({
            'Name': ['Rainfall'],
            'Source': ['~event~_rf.csv'],
            'Time': ['Time'],
            'Value': ['Rainfall'],
        })
    else:
        df_bc_dbase = gdf_raingages[['Name']].copy(deep=True)

        df_bc_dbase['Source'] = df_bc_dbase['Name'] + '_rf_~event~.csv'
        df_bc_dbase['Time'] = 'Time'
        df_bc_dbase['Value'] = 'Rainfall'

    bc_dbase_path = Path(bc_dbase_filename)
    bc_dbase_path.parent.mkdir(exist_ok=True, parents=True)
    if bc_dbase_path.exists():
        # we need to append to the file
        feedback.pushInfo(f'Appending to: {bc_dbase_path}')
        df_bc_dbase.to_csv(bc_dbase_path, mode='a', index=False, header=False)
    else:
        df_bc_dbase.to_csv(bc_dbase_path, mode='w', index=False)

    # write the curves to the files
    if len(global_storm_data) > 0:
        for row in df_global_storms.itertuples():
            gdf_rain = gdf_timeseries[gdf_timeseries['Name'] == row.Rainfall + '_rf'].copy(deep=True)
            gdf_rain = gdf_rain.rename(columns={'Value': 'Rainfall'})
            if row.OverrideMultiplier:
                gdf_rain['Rainfall'] = gdf_rain['Rainfall'] * row.Multiplier

            out_ts_filename = bc_dbase_path.parent / f'{row.Name}_rf.csv'
            gdf_rain[['Time', 'Rainfall']].to_csv(out_ts_filename, index=False, float_format='%.5g')

        # create a TEF file
        if tef_filename is not None:
            with open(tef_filename, 'w') as tef_file:
                for row in df_global_storms.itertuples():
                    tef_file.write(f'Define Event == {row.Name}\n')
                    tef_file.write(f'    BC Event Source == ~event~ | {row.Name}\n')
                    tef_file.write(f'End Define\n\n')
    else:
        for rain_name in df_bc_dbase['Name']:
            gdf_rain = gdf_timeseries[gdf_timeseries['Name'] == rain_name + '_rf'].copy(deep=True)
            gdf_rain = gdf_rain.rename(columns={'Value': 'Rainfall'})
            out_ts_filename = bc_dbase_path.parent / f'{rain_name}_rf_{event_name_default}.csv'
            gdf_rain[['Time', 'Rainfall']].to_csv(out_ts_filename, index=False, float_format='%.5g')

        # create a TEF file
        if tef_filename is not None:
            with open(tef_filename, 'w') as tef_file:
                tef_file.write(f'Define Event == {event_name_default}\n')
                tef_file.write(f'    BC Event Source == ~event~ | {event_name_default}\n')
                tef_file.write(f'End Define\n\n')

    return_info['Timeseries_curves'] = sorted(list(df_bc_dbase['Name']))

    gdf_junctions.to_file(gpkg_filename, layer=junctions_layername, driver='GPKG', index=False)
    if len(gdf_storage) > 0:
        gdf_storage.to_file(gpkg_filename, layer=storage_layername, driver='GPKG', index=False)
    gdf_outfalls.to_file(gpkg_filename, layer=outfalls_layername, driver='GPKG', index=False)
    gdf_conduits.to_file(gpkg_filename, layer=conduits_layername, driver='GPKG', index=False)

    if len(gdf_weirs) > 0:
        gdf_weirs.to_file(gpkg_filename, layer=weirs_layername, driver='GPKG', index=False)

    if len(gdf_orifices) > 0:
        gdf_orifices.to_file(gpkg_filename, layer=orifices_layername, driver='GPKG', index=False)

    if len(gdf_pumps) > 0:
        gdf_pumps.to_file(gpkg_filename, layer=pumps_layername, driver='GPKG', index=False)

    if len(gdf_subs) > 0:
        gdf_subs.to_file(gpkg_filename, layer=sub_layername, driver='GPKG', index=False)
    gdf_raingages.to_file(gpkg_filename, layer=raingages_layername, driver='GPKG', index=False)
    gdf_timeseries.to_file(gpkg_filename, layer='Curves--Timeseries', driver='GPKG', index=False)
    if len(gdf_title) > 0:
        gdf_title.to_file(gpkg_filename, layer=title_layername, driver='GPKG', index=False)

    gdf_options = gpd.GeoDataFrame(df_options, geometry=[None] * len(df_options.index))
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
        gdf_inlet_usage.to_file(iu_filename, layer='inlet_usage_001', driver='GPKG', index=False)

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

    return return_info


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.max_rows', 500)
    pd.set_option('display.width', 200)

    dest_folder = r'D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_25\test_convert\\'

    in_filename = Path(
        r'D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_23\TO1B_202103_20220525\TO1B.xpx')

    out_filename = Path(dest_folder + 'TO1B.gpkg')
    out_gis_layers_filename = Path(dest_folder + r'TO1B_layers.gpkg')
    out_iu_filename = Path(dest_folder + r'TO1B_iu.gpkg')
    bc_dbase_filename = Path(dest_folder + '/bcdbase/bcdbase.csv')

    messages_filename = Path(dest_folder + 'TO1B_messages.gpkg')
    event_name_default = 'event1'

    out_crs = ('EPSG:6434')

    xpx_to_gpkg(in_filename, out_filename, 1.0, 10.0, out_gis_layers_filename, out_iu_filename, messages_filename,
                bc_dbase_filename, event_name_default, None, out_crs)
