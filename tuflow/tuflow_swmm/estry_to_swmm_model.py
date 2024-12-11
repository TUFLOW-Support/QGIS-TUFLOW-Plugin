"""
This file converts an ESTRY model into SWMM (gpkg) format.
Initial focus will be on pipe network (pipes, nodes, and inlets)
Most of the information will come from check files because they have the processed elevation data
"""
import os

# os.environ['USE_PYGEOS'] = '0'

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false
from io import StringIO
import numpy as np
import pandas as pd
from pathlib import Path

from tuflow.tuflow_swmm.create_swmm_section_gpkg import create_section_gdf, create_section_from_gdf
from tuflow.tuflow_swmm.estry_to_swmm import *
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback

# TODO
# Do Irregular culverts (need to do spatial join with xsections)
# give a warning if operational channels are found
# Provide GIS warnings layer for unhandled features




def create_curves_from_dfs(curve_type, curve_names, df_curves, crs):
    gdf_curves = []

    for curve_name, df in zip(curve_names, df_curves):
        # Can't have spaces
        df['Name'] = curve_name.replace(' ', '_')
        curve_col_mapping = {
            'Name': 'Name',
            df.columns[0]: 'xval',
            df.columns[1]: 'yval',
        }

        gdf_curve, _ = create_section_from_gdf('Curves',
                                               crs,
                                               df,
                                               curve_col_mapping)
        gdf_curve['Type'] = ''
        gdf_curve['Description'] = ''
        gdf_curve.loc[gdf_curve.index[0], 'Type'] = curve_type
        gdf_curves.append(gdf_curve)

    gdf_curves_merged = pd.concat(gdf_curves)
    # print(gdf_curves_merged)

    return gdf_curves_merged


def create_hw_curves2(gdf, filename_ta_tables, crs, feedback):
    # Read in the check file looking for channels
    dfs_hw = {}  # dataframes for channel data by channel name

    with open(filename_ta_tables, "r") as f_ta:
        current_table = None
        current_table_lines = ""

        for line in f_ta:
            if current_table is None:
                if line.startswith('Channel'):
                    current_table = line.split(' ')[1]  # channel name is the second item
            else:
                if line.strip() == '':
                    # current table finished
                    df = pd.read_csv(StringIO(current_table_lines), sep=',', usecols=range(9), skipinitialspace=True)
                    print(df)
                    dfs_hw[current_table] = df
                    current_table = None
                    current_table_lines = ""
                else:
                    current_table_lines += f'\n{line}'

    # Handle last table if one found
    if current_table is not None:
        df = pd.read_csv(StringIO(current_table_lines), sep=',', usecols=range(9), skipinitialspace=True)
        print(df)
        dfs_hw[current_table] = df

    curve_names = []
    max_heights = []
    dfs = []

    # print(gdf['Link'])
    for _, (channel_name, *_) in gdf[['Link']].iterrows():
        print(channel_name)

        df_trim = dfs_hw[channel_name]

        df_trim = df_trim[['Depth', 'Flow Width']].rename(
            columns={
                'Depth': 'Height',
                'Flow Width': 'Width',
            }
        )
        print(df_trim)

        curve_names.append(str(channel_name))
        max_heights.append(df_trim['Height'].max())
        dfs.append(df_trim)

    return curve_names, max_heights, create_curves_from_dfs('SHAPE', curve_names, dfs, crs)


def ConvertEstryToSwmmFolders(tuflow_folder,
                              check_subfolder,
                              estry_sim,
                              gpkg_check_files,
                              swmm_subfolder,
                              swmm_output_name,
                              crs,
                              default_pond_area,
                              street_name,
                              street_slope_pct,
                              report_step,
                              min_surfarea,
                              pit_inlet_dbase_filename,
                              inlet_placement,
                              filename_ext_inlet_usage,
                              reference_cell_size,
                              feedback=ScreenProcessingFeedback(),
                              ):
    check_folder = tuflow_folder / check_subfolder
    if not gpkg_check_files:
        feedback.reportError('Only GeoPackage ESTRY check files are currently supported.')
    check_filename = check_folder / f'{estry_sim}_Check.gpkg'

    pit_inlet_dbase_path = tuflow_folder / pit_inlet_dbase_filename

    swmm_out_filename = tuflow_folder / swmm_subfolder / f'{swmm_output_name}.gpkg'

    filename_ta_check = check_folder / f'{estry_sim}_1d_ta_tables_check.csv'

    ext_pathfilename = tuflow_folder / swmm_subfolder / f'{filename_ext_inlet_usage}.gpkg'

    ConvertEstryToSwmm(check_filename,
                       pit_inlet_dbase_path,
                       filename_ta_check,
                       swmm_out_filename,
                       crs,
                       default_pond_area,
                       street_name,
                       street_slope_pct,
                       report_step,
                       min_surfarea,
                       inlet_placement,
                       ext_pathfilename,
                       reference_cell_size,
                       feedback)


def ConvertEstryToSwmm(check_filename,
                       pit_inlet_dbase_path,
                       filename_ta_check,
                       swmm_out_filename,
                       crs,
                       default_pond_area,
                       street_name,
                       street_slope_pct,
                       report_step,
                       min_surfarea,
                       inlet_placement,
                       filename_ext_inlet_usage,
                       reference_cell_size,
                       feedback=ScreenProcessingFeedback(),
                       ):
    # Create the curves table based upon the pit_inlet_dbase
    gdf_curves, curves_layername = pit_inlet_dbase_to_df(pit_inlet_dbase_path, crs, feedback)

    gdf_check_nwk_c = None
    gdf_check_nwk_n = None
    gdf_check_mhc = None
    gdf_check_iwl = None
    gdf_check_hydroprop = None
    gdf_check_pitA = None
    gdf_check_1d2d = None
    gdf_check_xsl = None

    check_files_gpkg = True

    if check_files_gpkg:
        # Remove _check from main part of filename to get ESTRY sim name
        estry_sim = str(check_filename.stem)[:-6]
        feedback.pushInfo(f'ESTRY simulation: {estry_sim}')

        check_c_layername = f'{estry_sim}_nwk_C_check_L'
        gdf_check_nwk_c = gpd.read_file(check_filename, layer=check_c_layername)
        if crs == "":
            crs = gdf_check_nwk_c.crs

        check_n_layername = f'{estry_sim}_nwk_N_check_P'
        gdf_check_nwk_n = gpd.read_file(check_filename, layer=check_n_layername)

        check_mhc_layername = f'{estry_sim}_mhc_check_P'
        gdf_check_mhc = gpd.read_file(check_filename, layer=check_mhc_layername)

        check_iwl_layername = f'{estry_sim}_IWL_check_P'
        gdf_check_iwl = gpd.read_file(check_filename, layer=check_iwl_layername)

        check_hydroprop_layername = f'{estry_sim}_hydprop_check_L'
        gdf_check_hydroprop = gpd.read_file(check_filename, layer=check_hydroprop_layername)

        check_pitA_layername = f'{estry_sim}_pit_A_check_P'
        gdf_check_pitA = gpd.read_file(check_filename, layer=check_pitA_layername)

        check_1d2d_layername = f'{estry_sim}_1d_to_2d_check_R'
        gdf_check_1d2d = gpd.read_file(check_filename, layer=check_1d2d_layername)

        check_xsl_layername = f'{estry_sim}_xsl_check_L'
        gdf_check_xsl = gpd.read_file(check_filename, layer=check_xsl_layername)

    feedback.pushInfo(f'Number of channels in ESTRY check file: {len(gdf_check_nwk_c)}')

    # feedback.pushDebugInfo(gdf_check_nwk_n)
    gdf_check_nwk_n = gpd.sjoin(
        gdf_check_nwk_n,
        gdf_check_mhc,
        how='left',
        lsuffix='remove',
        rsuffix='mh'
    )

    gdf_check_nwk_n.columns = [x.replace('_remove', '') for x in gdf_check_nwk_n.columns]

    gdf_check_nwk_n = gpd.sjoin(
        gdf_check_nwk_n,
        gdf_check_iwl,
        how='left',
        lsuffix='remove',
        rsuffix='iwl'
    )
    gdf_check_nwk_n.columns = [x.replace('_remove', '') for x in gdf_check_nwk_n.columns]

    # we need this information to set surcharge height high for nodes without inlets
    gdf_check_nwk_n = gdf_check_nwk_n.merge(
        gdf_check_pitA,
        how='left',
        left_on='ID',
        right_on='ID',
        suffixes=('', '_pitA'),
    )

    # print(gdf_check_nwk_n)

    gdf_check_nwk_c = gdf_check_nwk_c.merge(
        gdf_check_hydroprop,
        how='left',
        left_on='ID',
        right_on='ID',
        suffixes=('', '_hyd')
    )
    gdf_check_nwk_c.columns = [x.replace('_remove', '') for x in gdf_check_nwk_c.columns]
    feedback.pushInfo(f'Number of channels in check file: {len(gdf_check_nwk_c)}')

    # print(gdf_check_nwk_c.columns)
    # print(gdf_check_nwk_n.columns)
    # print(gdf_check_mhc.columns)

    # swmm_out_filename = tuflow_folder / swmm_subfolder / f'{swmm_output_name}.gpkg'

    # by default ymax is bassed upon highest_soffit (if 0 SWMM will use top of adjacent pipe)
    gdf_check_nwk_n.loc[:, 'Ymax'] = gdf_check_nwk_n['Highest_Soffit']


    pita_inlet_types = ['C', 'Q', 'R', 'W']

    # print(gdf_check_nwk_n)

    if 'Invert' not in gdf_check_nwk_n.columns:
        gdf_check_nwk_n['Invert'] = gdf_check_nwk_n['Invert_Level']

    # we need the .1 versions (without the .1) to get the Conn_1D_2D and Conn_Width entries
    gdf_check_nwk_n_pits = gdf_check_nwk_n[gdf_check_nwk_n['ID'].str.endswith('.1')].copy()
    gdf_check_nwk_n_pits['ID'] = gdf_check_nwk_n_pits['ID'].str.replace('.1', '')
    gdf_check_nwk_n = pd.merge(gdf_check_nwk_n, gdf_check_nwk_n_pits[['ID', 'Conn_1D_2D', 'Conn_Width', 'Bed_Level']],
                               'left', 'ID', suffixes=('', '_pit'))

    # if there is a pit(inlet) make the Ymax equal based upon invert
    gdf_check_nwk_n.loc[gdf_check_nwk_n['Type_pitA'].isin(pita_inlet_types), 'Ymax'] = \
        gdf_check_nwk_n.loc[gdf_check_nwk_n['Type_pitA'].isin(pita_inlet_types), 'Bed_Level_pit']

    # print(gdf_check_nwk_n[gdf_check_nwk_n['ID'] == 'SP72879705_O'])

    # if there is an inlet use it for surcharge height. Otherwise, set it very large
    # Users will need to decrease it at boundary conditions
    gdf_check_nwk_n['Surcharge'] = '100.0'

    # nodes connected to pits or 1D/2d boundaries should be able to surcharge
    # RDJ - Temp lets not let q inlets surcharge - didn't have good results go back for now
    # pita_inlet_types_except_q = ['C', 'R', 'W']
    gdf_check_nwk_n['CanSpill'] = (gdf_check_nwk_n['Type_pitA'].isin(pita_inlet_types)) | \
                                  (gdf_check_nwk_n['ID'].isin(gdf_check_1d2d['Primary_Node'].unique())) | \
                                  (gdf_check_nwk_n['ID'].isin(gdf_check_1d2d['Secondary_Node'].unique()))
    gdf_check_nwk_n.loc[gdf_check_nwk_n['CanSpill'], 'Surcharge'] = 0.0

    print(gdf_check_nwk_n)

    gdf_check_nwk_n['Apond'] = default_pond_area
    nwk_to_junction_cols = {
        'ID': 'Name',
        'Bed_Level': 'Elev',
        'Ymax': 'Ymax',
        'IWL': 'Y0',
        'Apond': 'Apond',
        'Surcharge': 'Ysur',
        'geometry': 'geometry',
    }
    gdf_junctions, junctions_layername = create_section_from_gdf('Junctions',
                                                                 crs,
                                                                 gdf_check_nwk_n,
                                                                 nwk_to_junction_cols)
    gdf_junctions['Ymax'] = gdf_junctions['Yma)'].astype(float) - gdf_junctions['Elev'].astype(float)
    gdf_junctions.loc[gdf_junctions['Ymax'].isna(), 'Ymax'] = 0.


    gdf_junctions['Y0'] = (gdf_junctions['Y0'] - gdf_junctions['Elev']).clip(lower=0.0)


    # print(gdf_junctions)

    # For pipes only use types C, I, R, Weirs (W,WB,WC,WD,WO,WR,WT,WV,WW), M, Q
    # We may end up with some open channel segments but the user will need to clean that up
    pipe_channel_types = [
        'C',
        'R',
        'I',
    ]
    # Remove flags and store information elsewhere

    gdf_check_nwk_c['Unidirectional'] = gdf_check_nwk_c['Type'].str.contains('U')
    gdf_check_nwk_c['Type_mod'] = gdf_check_nwk_c['Type'].str.replace('U', '')

    gdf_check_nwk_c['Weir_over_top'] = gdf_check_nwk_c['Type_mod'].isin(['CW', 'RW'])
    gdf_check_nwk_c.loc[
        gdf_check_nwk_c['Weir_over_top'],
        'Type_mod'
    ].str.replace('W', '')

    gdf_check_nwk_c['Operational'] = gdf_check_nwk_c['Type_mod'].str.contains('O')
    gdf_check_nwk_c['Type_mod'] = gdf_check_nwk_c['Type_mod'].str.replace('O', '')

    # We need to remove Pit channels
    # They aren't clearly marked but the name and downstream name are the same
    gdf_check_nwk_c = gdf_check_nwk_c[gdf_check_nwk_c['ID'] != gdf_check_nwk_c['DS_Node_ID']]
    gdf_check_nwk_c.crs = crs

    gdf_nwk_pipes = gdf_check_nwk_c.copy(deep=True)
    gdf_nwk_pipes = gdf_nwk_pipes[gdf_nwk_pipes['Type_mod'].isin(pipe_channel_types)]

    nwkc_to_conduits_map = \
        {
            'ID': 'Name',
            'US_Node_ID': 'From Node',
            'DS_Node_ID': 'To Node',
            'Len_or_ANA': 'Length',
            'n_nF_Cd': 'Roughness',
            'US_Invert': 'InOffset',
            'DS_Invert': 'OutOffset',
            'geometry': 'geometry',
        }
    gdf_conduits, conduits_layername = create_section_from_gdf('Conduits',
                                                               crs,
                                                               gdf_nwk_pipes,
                                                               nwkc_to_conduits_map)

    feedback.pushInfo(f'Number of conduits: {len(gdf_conduits)}')
    df_node_elevs = gdf_check_nwk_n.set_index('ID').loc[
        gdf_conduits['From Node'], 'Bed_Level'
    ]

    # print(df_node_elevs)
    gdf_conduits['InOffset'] -= df_node_elevs.values
    gdf_conduits['InOffset'] = gdf_conduits['InOffset'].clip(lower=0.0)
    df_node_elevs = gdf_check_nwk_n.set_index('ID').loc[
        gdf_conduits['To Node'], 'Bed_Level'
    ]
    gdf_conduits['OutOffset'] -= df_node_elevs.values
    gdf_conduits['OutOffset'] = gdf_conduits['OutOffset'].clip(lower=0.0)

    # print(gdf_conduits)
    # print(f'Number of conduits: {len(gdf_conduits)}')

    # Handle pumps
    gdf_nwk_pumps = gdf_check_nwk_c.copy(deep=True)
    # print(gdf_nwk_pumps['Type_mod'].unique())
    gdf_nwk_pumps = gdf_nwk_pumps[gdf_nwk_pumps['Type_mod'] == 'P']
    feedback.pushInfo(f'Number of pumps: {len(gdf_nwk_pumps)}')
    gdf_nwk_pumps['PumpCurve'] = gdf_nwk_pumps['ID']
    gdf_nwk_pumps['Status'] = 'OFF'
    nwkc_to_pumps_map = \
        {
            'ID': 'Name',
            'US_Node_ID': 'From Node',
            'DS_Node_ID': 'To Node',
            'PumpCurve': 'PCurve',
            'Status': 'Status',
            'geometry': 'geometry',
        }
    gdf_pumps, pumps_layername = create_section_from_gdf('Pumps',
                                                         crs,
                                                         gdf_nwk_pumps,
                                                         nwkc_to_pumps_map)

    df_pump_elevations = gdf_nwk_pumps[['ID', 'US_Invert']]

    # TODO - Give warning for pumps need to define curves and possibly controls

    # print(gdf_check_nwk_c[gdf_check_nwk_c['ID'] == 'MHCRSP.1'])
    gdf_nwk_weirs = gdf_check_nwk_c.copy(deep=True)
    gdf_nwk_weirs = gdf_nwk_weirs[gdf_nwk_weirs['Type_mod'].str.startswith('W')]
    feedback.pushInfo(f'Number of weirs: {len(gdf_nwk_weirs)}')

    # TODO - Give warning for weir types not supported by SWMM
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

    # print(gdf_nwk_weirs['US_Node_ID'])
    gdf_junctions_indexed = gdf_junctions.set_index('Name')
    # print(gdf_junctions_indexed)
    # print(set(gdf_nwk_weirs['US_Node_ID']) - set(gdf_junctions_indexed.index))
    # print(gdf_junctions_indexed.loc['JNT_1308035.1', :])
    gdf_nwk_weirs['CrestHt'] = gdf_nwk_weirs[['US_Invert', 'DS_Invert']].max(axis=1) - \
                               gdf_junctions_indexed.loc[gdf_nwk_weirs['US_Node_ID'], 'Elev'].values
    gdf_nwk_weirs['WeirType'] = gdf_nwk_weirs['Type_mod'].apply(lambda x: weir_type_mapping[x])
    gdf_nwk_weirs['Cd'] = gdf_nwk_weirs['Type_mod'].apply(lambda x: weir_coeff_mapping[x])
    gdf_nwk_weirs['Gated'] = gdf_nwk_weirs['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
    # overwrite if not 0
    gdf_nwk_weirs.loc[
        gdf_nwk_weirs['HConF_or_WC'] > 0.0, 'Cd'
    ] = gdf_nwk_weirs.loc[
        gdf_nwk_weirs['HConF_or_WC'] > 0.0, 'HConF_or_WC']
    # Handle multipliers
    gdf_nwk_weirs.loc[
        gdf_nwk_weirs['Height_or_WF'] > 0.0, 'Cd'
    ] *= gdf_nwk_weirs.loc[
        gdf_nwk_weirs['Height_or_WF'] > 0.0, 'Height_or_WF']

    nwkc_to_weirs_map = \
        {
            'ID': 'Name',
            'US_Node_ID': 'From Node',
            'DS_Node_ID': 'To Node',
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

    gdf_nwk_weirs.loc[
        gdf_nwk_weirs['WeirGeom2'] == 0.0, 'WeirGeom2'] = gdf_nwk_weirs.loc[
        gdf_nwk_weirs['WeirGeom2'] == 0.0, 'Flow_Width']
    gdf_nwk_weirs.loc[:, ['WeirGeom3', 'WeirGeom4']] = 0.0
    gdf_nwk_weirs.loc[
        gdf_nwk_weirs['WeirType'] == 'TRAPEZOIDAL', ['WeirGeom3', 'WeirGeom4']] = 1.0

    nwkc_to_weir_xsecs_map = {
        'ID': 'Link',
        'WeirShape': 'Shape',
        'WeirGeom1': 'Geom1',
        'WeirGeom2': 'Geom2',
        'WeirGeom3': 'Geom3',
        'WeirGeom4': 'Geom4',
        'geometry': 'geometry'
    }
    gdf_weir_xsecs, _ = create_section_from_gdf('XSections',
                                                crs,
                                                gdf_nwk_weirs,
                                                nwkc_to_weir_xsecs_map)

    # Handle Sluice Gates (become orifices)
    gdf_orifices = None
    gdf_nwk_sg = gdf_check_nwk_c.copy(deep=True)
    gdf_nwk_sg = gdf_nwk_sg[gdf_nwk_sg['Type_mod'].str.startswith('SG')]
    gdf_sg_xsecs = None
    orifices_layername = None

    if len(gdf_nwk_sg) > 0:
        gdf_nwk_sg['SgType'] = 'SIDE'
        gdf_nwk_sg['Gated'] = gdf_nwk_sg['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
        gdf_nwk_sg['Offset'] = 0.0
        nwkc_sg_to_orifices_map = \
            {
                'ID': 'Name',
                'US_Node_ID': 'From Node',
                'DS_Node_ID': 'To Node',
                'SgType': 'Type',
                'Offset': 'Offset',
                'n_nF_Cd': 'Qcoeff',
                'Gated': 'Gated',
                'geometry': 'geometry',
            }
        gdf_orifices, orifices_layername = create_section_from_gdf('Orifices',
                                                                   crs,
                                                                   gdf_nwk_sg,
                                                                   nwkc_sg_to_orifices_map)

        gdf_nwk_sg_xsecs = gdf_check_nwk_c.copy(deep=True)
        gdf_nwk_sg_xsecs = gdf_nwk_sg_xsecs[gdf_nwk_sg_xsecs['Type_mod'].str.startswith('SG')]
        if len(gdf_nwk_sg_xsecs) > 0:
            gdf_nwk_sg_xsecs['Shape'] = 'RECT_CLOSED'
            gdf_nwk_sg_xsecs['Geom3'] = 0
            gdf_nwk_sg_xsecs['Geom4'] = 0
            nwkc_sg_to_orifices_xsecs_map = {
                'ID': 'Link',
                'Shape': 'Shape',
                'Height_or_WF': 'Geom1',
                'Width_or_Dia': 'Geom2',
                'Geom3': 'Geom3',
                'Geom4': 'Geom4',
                'geometry': 'geometry'
            }
            gdf_sg_xsecs, _ = create_section_from_gdf('XSections',
                                                      crs,
                                                      gdf_nwk_sg_xsecs,
                                                      nwkc_sg_to_orifices_xsecs_map)

    # Handle Q Channels (become outlets)
    gdf_outlets = None
    outlets_layername = None
    gdf_nwk_q = gdf_check_nwk_c.copy(deep=True)
    gdf_nwk_q = gdf_nwk_q[gdf_nwk_q['Type_mod'].str.startswith('Q')]
    feedback.pushInfo(f'Number of Q inlets: {len(gdf_nwk_q)}')
    if len(gdf_nwk_q) > 0:
        gdf_nwk_q['OutletType'] = 'TABULAR/DEPTH'
        gdf_nwk_q['Gated'] = gdf_nwk_sg['Unidirectional'].apply(lambda x: 'YES' if x else 'NO')
        gdf_nwk_q['Offset'] = 0.0
        nwkc_q_to_outlets_map = \
            {
                'ID': 'Name',
                'US_Node_ID': 'From Node',
                'DS_Node_ID': 'To Node',
                'Offset': 'Offset',
                'OutletType': 'Type',
                'Inlet_Type': 'TABULAR/DEPTH',
                'Gated': 'Gated',
                'geometry': 'geometry',
            }
        gdf_outlets, outlets_layername = create_section_from_gdf('Outlets',
                                                                 crs,
                                                                 gdf_nwk_q,
                                                                 nwkc_q_to_outlets_map)
        # Can't have spaces
        gdf_outlets['Param1'] = gdf_outlets['Param1'].str.replace(' ', '_')

        gdf_nwk_sg_xsecs = gdf_check_nwk_c.copy(deep=True)
        gdf_nwk_sg_xsecs = gdf_nwk_sg_xsecs[gdf_nwk_sg_xsecs['Type_mod'].str.startswith('SG')]
        gdf_nwk_sg_xsecs['Shape'] = 'RECT_CLOSED'
        gdf_nwk_sg_xsecs['Geom3'] = 0
        gdf_nwk_sg_xsecs['Geom4'] = 0
        nwkc_sg_to_orifices_xsecs_map = {
            'ID': 'Link',
            'Shape': 'Shape',
            'Height_or_WF': 'Geom1',
            'Width_or_Dia': 'Geom2',
            'Geom3': 'Geom3',
            'Geom4': 'Geom4',
            'geometry': 'geometry'
        }
        gdf_sg_xsecs, _ = create_section_from_gdf('XSections',
                                                  crs,
                                                  gdf_nwk_sg_xsecs,
                                                  nwkc_sg_to_orifices_xsecs_map)

    # Convert the nwk_c to get Geom1 and Geom2
    gdf_check_nwk_c['Geom1'] = gdf_check_nwk_c['Width_or_Dia']
    gdf_check_nwk_c.loc[gdf_check_nwk_c['Type_mod'] == 'R', 'Geom1'] = gdf_check_nwk_c.loc[
        gdf_check_nwk_c['Type_mod'] == 'R', 'Height_or_WF']
    gdf_check_nwk_c['Geom2'] = gdf_check_nwk_c['Width_or_Dia']

    gdf_check_pipes = gdf_check_nwk_c.copy(deep=True)
    gdf_check_pipes['Geom3'] = 0
    gdf_check_pipes['Geom4'] = 0

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
                                                         gdf_check_pipes,
                                                         nwk_c_to_xsecs_map)

    gdf_xsecs['XsecType'] = gdf_check_pipes['Type_mod'].map(lambda x: 'CIRCULAR' if x.startswith('C')
    else 'RECT_CLOSED' if x.startswith('R') else 'CUSTOM')

    gdf_xsecs = gdf_xsecs[gdf_xsecs['Link'].isin(gdf_conduits['Name'])]

    gdf_irr_culv_curves = None
    if len(gdf_xsecs[gdf_xsecs['XsecType'] == 'CUSTOM']) > 0:
        custom_xsecs = gdf_xsecs['XsecType'] == 'CUSTOM'
        gdf_irr_culv_xsec = gdf_xsecs[custom_xsecs]
        # don't use this check file because we want processessed H/W
        # == 'CUSTOM'].sjoin(
        #     gdf_check_xsl,
        #     how='left',
        #     lsuffix='remove',
        #     rsuffix='xsl'
        # )
        # print(gdf_irr_culv_xsec)
        #
        irr_curve_names, max_heights, gdf_irr_culv_curves = create_hw_curves2(gdf_irr_culv_xsec, filename_ta_check,
                                                                              crs, feedback)

        gdf_xsecs.loc[custom_xsecs, 'Geom1'] = max_heights
        gdf_xsecs.loc[custom_xsecs, 'Curve'] = irr_curve_names
        gdf_xsecs.loc[custom_xsecs, 'Dummy'] = 0.0

    gdf_xsecs.crs = crs

    gdf_check_nwk_c['Flap Gate'] = 'No'
    gdf_check_nwk_c.loc[gdf_check_nwk_c['Unidirectional'], 'Flap Gate'] = 'Yes'
    nwk_c_to_losses_map = {
        'ID': 'Link',
        'EntryC_or_WSa': 'Kentry',
        'ExitC_or_WSb': 'Kexit',
        'Form_Loss': 'Kavg',
        'Flap Gate': 'Flap',
        'geometry': 'geometry',
    }
    gdf_losses, losses_layername = create_section_from_gdf('Losses',
                                                           crs,
                                                           gdf_check_nwk_c,
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




    gdf_check_pitA = gpd.sjoin(
        gdf_check_pitA,
        gdf_check_nwk_n,
        how='left',
        lsuffix='remove',
        rsuffix='nwk_n',
    )
    gdf_check_pitA.columns = [x.replace('_remove', '') for x in gdf_check_pitA.columns]
    # print(gdf_check_pitA)

    gdf_inlets_q = None

    inlets_layername = ''

    # For Q inlets, we will use custom curves
    gdf_check_pitA_Q = gdf_check_pitA[gdf_check_pitA['Type_pitA'] == 'Q']

    # print(gdf_check_pitA_Q)
    # print(gdf_check_pitA_Q['Conn_1D_2D'])
    if len(gdf_check_pitA_Q) > 0:
        gdf_inlets_temp = gpd.GeoDataFrame(
            data={'Inlet_Type': gdf_check_pitA_Q['Inlet_Type'].unique()},
            geometry=gpd.GeoSeries())
        gdf_inlets_temp['geometry'] = None
        # print(gdf_inlets_temp)
        # print(type(gdf_inlets_temp))
        inlet_q_to_inlets_map = {
            'Inlet_Type': 'Name',
            'geometry': 'geometry',
        }

        gdf_inlets_q, inlets_layername = create_section_from_gdf('Inlets',
                                                                 crs,
                                                                 gdf_inlets_temp,
                                                                 inlet_q_to_inlets_map)

        # gdf_inlets_q, inlets_layername = create_section_gdf('INLETS', crs)

        gdf_inlets_q['Type'] = 'CUSTOM'
        gdf_inlets_q['Custom_Curve'] = gdf_inlets_q['Name']
        # print(gdf_inlets_q)
        # print(type(gdf_inlets_q))

    # We need to make inlet types for any C, R, or W types

    # W types weirs - represent as a curb with similar perimeter to width (used as weir length in TUFLOW)
    gdf_check_pitA_W = gdf_check_pitA[gdf_check_pitA['Type_pitA'] == 'W']
    gdf_inlets_w = None
    if len(gdf_check_pitA_W) > 0:
        feedback.pushInfo(f'Number of W inlets: {len(gdf_check_pitA_W)}')

        grate_widths = sorted(gdf_check_pitA_W['Width'].unique())

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
                'Grate_Length': grate_lengths,
                'Grate_Width': grate_heights,
                'Grate_Type': throat,
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
        # Set names for W grates
        gdf_check_pitA.loc[
            gdf_check_pitA['Type_pitA'] == 'W', 'Inlet_Type'
        ] = gdf_check_pitA[
            gdf_check_pitA['Type_pitA'] == 'W'
            ]['Width'].apply(lambda x: f'W_{int(x * 1000)}')

    # TODO R, C types

    gdfs_inlets = []
    if gdf_inlets_w is not None:
        gdfs_inlets.append(gdf_inlets_w)
    if gdf_inlets_q is not None:
        gdfs_inlets.append(gdf_inlets_q)

    if len(gdfs_inlets) > 0:
        gdf_inlets = pd.concat(
            gdfs_inlets
        )
    else:
        gdf_inlets = None

    gdf_inlets = gdf_inlets[gdf_inlets['Name'] != 'dummy']
    # print(gdf_inlets)
    # print(inlets_layername)

    # gdf_inlets_q = gdf_inlets_q[gdf_inlets_q['Name'] != 'dummy']

    # print(gdf_check_pitA)
    # print(gdf_check_pitA['Conn_1D_2D'].unique())

    gdf_inlet_usage_ext = None
    gdf_inlet_usage = None
    gdf_street_conduits = None
    gdf_street_xsecs = None
    gdf_street_junctions = None
    gdf_streets = None

    check_pitA_to_inlet_usage_map = {
        'Inlet_Type': 'Inlet',
        'Number_of': 'Number',
        'pBlockage': 'CloggedPct',
        'Bed_Level_pit': 'Elevation',
        'geometry': 'geometry',
        'Conn_1D_2D_pit': 'Conn1D_2D',
        'Conn_Width_pit': 'Conn_width'
    }
    gdf_inlet_usage_ext, inlet_usage_ext_layername = create_section_from_gdf('Inlet_Usage_ext',
                                                                             crs,
                                                                             gdf_check_pitA,
                                                                             check_pitA_to_inlet_usage_map)

    gdf_inlet_usage_ext['Number'] = gdf_inlet_usage_ext['Number'].clip(lower=1)

    gdf_inlet_usage_ext['StreetXSEC'] = street_name
    gdf_inlet_usage_ext['SlopePct_Long'] = street_slope_pct
    gdf_inlet_usage_ext['Qmax'] = 0.0  # No restriction
    gdf_inlet_usage_ext['aLocal'] = 0.0
    gdf_inlet_usage_ext['wLocal'] = 0.0
    gdf_inlet_usage_ext['Placement'] = 'ON_SAG'

    # Change L to Z in SX connections because we will use the previoulsy extracted elevation
    gdf_inlet_usage_ext['Conn1D_2D'] = gdf_inlet_usage_ext['Conn1D_2D'].str[:2] +\
        gdf_inlet_usage_ext['Conn1D_2D'].str[2:].replace('L', 'Z')

    # Connection width is number of cells if negative but must be converted to a width if positive
    gdf_inlet_usage_ext.loc[gdf_inlet_usage_ext['Conn_width'] > 0.0, 'Conn_width'] = gdf_inlet_usage_ext.loc[
                                                                                         gdf_inlet_usage_ext[
                                                                                             'Conn_width'] > 0.0,
                                                                                         'Conn_width'].astype(
        float) * reference_cell_size

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
    # print(gdf_streets)

    # print(gdf_street_conduits)

    gdf_options, options_layername = default_options_table(crs, report_step, min_surfarea)

    gdf_report, report_layername = default_reporting_table(crs)

    gdf_conduits.crs = crs

    gdf_xsecs = pd.concat(
        [gdf_xsecs, gdf_weir_xsecs, gdf_sg_xsecs],
        axis=0
    )
    gdf_xsecs.crs = crs

    # Junctions have to be in an upstream node (from node)
    all_channel_dfs = [gdf_conduits]
    if len(gdf_weirs) > 0:
        all_channel_dfs.append(gdf_weirs)
    if len(gdf_pumps) > 0:
        all_channel_dfs.append(gdf_pumps)
    if gdf_orifices is not None:
        all_channel_dfs.append(gdf_orifices)
    if gdf_outlets is not None:
        all_channel_dfs.append(gdf_outlets)

    all_from_nodes = pd.concat(all_channel_dfs, axis=0)['From Node'].unique()
    gdf_all_nodes = gdf_junctions.copy(deep=True)
    gdf_junctions = gdf_junctions[
        (gdf_junctions['Name'].isin(all_from_nodes))
    ]

    # outfalls
    all_to_nodes = pd.concat(all_channel_dfs, axis=0)['To Node'].unique()
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

    # Geo-Package for external inlets
    ext_pathfilename = filename_ext_inlet_usage
    if gdf_inlet_usage_ext is not None:
        gdf_inlet_usage_ext.to_file(ext_pathfilename,
                                    layer='inlet_usage',
                                    driver='GPKG')

    # We will save a Geo-Package and SWMM representation
    swmm_out_filename = swmm_out_filename.with_suffix('.gpkg')

    # Make sure the parent folder exists
    swmm_out_filename.parent.mkdir(parents=True, exist_ok=True)

    if len(df_pump_elevations) > 0:
        pump_elevation_filename = swmm_out_filename.with_stem(swmm_out_filename.stem + '_pump_elevations') \
            .with_suffix('.xlsx')
        df_pump_elevations.to_excel(pump_elevation_filename)

    # see if the file already exists and if so delete it
    if swmm_out_filename.exists():
        swmm_out_filename.unlink()

    feedback.pushInfo(f'Writing geo-database information to file: {swmm_out_filename}\n')
    # print(type(gdf_options))
    gdf_options.to_file(swmm_out_filename,
                        layer=options_layername,
                        driver='GPKG')

    gdf_report.to_file(swmm_out_filename,
                       layer=report_layername,
                       driver='GPKG')

    gdf_conduits.to_file(swmm_out_filename,
                         layer=conduits_layername,
                         driver='GPKG')

    if len(gdf_pumps) > 0:
        gdf_pumps.to_file(swmm_out_filename,
                          layer=pumps_layername,
                          driver='GPKG')

    if len(gdf_weirs) > 0:
        gdf_weirs.to_file(swmm_out_filename,
                          layer=weirs_layername,
                          driver='GPKG')

    if gdf_orifices is not None:
        gdf_orifices.to_file(swmm_out_filename,
                             layer=orifices_layername,
                             driver='GPKG')

    if gdf_outlets is not None:
        gdf_outlets.to_file(swmm_out_filename,
                            layer=outlets_layername,
                            driver='GPKG')

    gdf_xsecs.to_file(swmm_out_filename,
                      layer=xsecs_layername,
                      driver='GPKG')

    if len(gdf_losses) > 0:
        gdf_losses.to_file(swmm_out_filename,
                           layer=losses_layername,
                           driver='GPKG')

    gdf_junctions.to_file(swmm_out_filename,
                          layer=junctions_layername,
                          driver='GPKG')

    gdf_outfalls.to_file(swmm_out_filename,
                         layer=outfalls_layername,
                         driver='GPKG')

    gdf_inlets.to_file(swmm_out_filename,
                       layer=inlets_layername,
                       driver='GPKG',
                       index=False)

    gdf_streets.to_file(swmm_out_filename,
                        layer=streets_layername,
                        driver='GPKG')

    # print(gdf_curves.dtypes)
    if len(gdf_irr_culv_curves) > 0:
        gdf_curves = gpd.GeoDataFrame(pd.concat([gdf_curves, gdf_irr_culv_curves]))
    # print(type(gdf_curves))
    # print(gdf_curves)
    # print(gdf_curves.dtypes)
    # There can't be spaces in the name
    gdf_curves['Name'] = gdf_curves['Name'].str.replace(' ', '_')
    # gdf_curves.to_csv("D:\\temp\\test_out.csv", index=False)
    gdf_curves.to_file(swmm_out_filename,
                       layer=curves_layername,
                       driver='GPKG')

    swmm_inp_filename = swmm_out_filename.with_suffix('.inp')
    gis_to_swmm(swmm_out_filename,
                swmm_inp_filename)


if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.min_rows', 50)
    pd.set_option('display.max_rows', 50)
    pd.set_option('display.width', 300)
    pd.set_option('max_colwidth', 100)

    report_step = '0:05:00'
    min_surfarea = '3'
    pond_area = 0.0
    street_name = 'DummyStreet'
    # street_offset = (0, -1)
    street_slope_pct = 4.0
    # street_length = 10
    # street_roughness = 0.018

    # For external inlets
    reference_cell_size = 5.0

    # TUFLOW always acts as if on sag
    inlet_placement = ['Auto', 'OnSag'][1]

    tuflow_folder = Path(r"D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW")
    check_subfolder = 'check'
    swmm_subfolder = 'model\\SWMM'
    estry_sim = 'sb_Q100_24hr_SBW_QT02_050CL_____100'
    gpkg_check_files = True
    swmm_output_name = 'sb_w_pipes_wide'
    pit_inlet_dbase = "model\\pit_dbase\\SB_pit_dbase_042.csv"
    crs = 'EPSG:6424'

    sim = ['ventura_w', 'bankstown'][1]
    if sim == 'bankstown':
        tuflow_folder = Path(r"D:\models\TUFLOW\test_models\SWMM\Bankstown_C13_rdj\TUFLOW")
        estry_sim = 'C13_test_HPC_5m_SGS___MULTICELL_005'
        swmm_output_name = 'c13_002b'
        pit_inlet_dbase = "pit_dbase\\BIV_pit_dbase_001B.csv"
        crs = 'EPSG:28356'
        report_step = '0:01:00'

    # For external inlets
    external_gpkg_filename = f'{swmm_output_name}_ext'

    print('Converting ESTRY to SWMM (hardcoded)')
    ConvertEstryToSwmmFolders(tuflow_folder, check_subfolder, estry_sim,
                              gpkg_check_files, swmm_subfolder, swmm_output_name,
                              crs, pond_area, street_name,
                              street_slope_pct,
                              report_step, min_surfarea, pit_inlet_dbase, inlet_placement,
                              external_gpkg_filename, reference_cell_size)
