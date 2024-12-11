import os

# os.environ['USE_PYGEOS'] = '0'

import pandas as pd
from pathlib import Path

from swmm_to_gis import swmm_to_gpkg
from gis_to_swmm import gis_to_swmm

if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.max_rows', 500)
    pd.set_option('display.width', 200)

    tags_to_filter = None

    # Used if you want to use a different filename to convert to inp file
    gpkg_to_swmm_filename = None

    # if specified it will read it for crs
    crs_filename = None

    model = [
        'OneChannel',
        'OneChannel_storage',
        'SF',
        'SF_results',
        'OneStreet',
        'Mijoulan',
        'Mijoulan_catchments',
        'Mijoulan_OnePipe',
        'Mijoulan_003',
        'Mijoulan_003_losses',
        'Mijoulan_004_inlets',
        'ExModels',
        'ExModels_results',
        'ExModels_addverts',
        'ExModels_EstryOpenChans',
        'Ruskin',
        'Ruskin_results',
        'OneD1d',
        'Ventura-Arundell1',
        'Ventura-Arundell2',
        'Ventura-AutoCenter',
        'Ventura-Brown',
        'Ventura-Hall_Canyon',
        'Ventura-Harmon',
        'Ventura-SuddenClarke',
        'Ventura-West1',
        'Ventura-West2',
        'Ventura-SBW',
        'Ventura-SBW-Losses',
        'Mijoulan_005_inlets',
        'Mijoulan_005b_inlets',
    ][-2]

    if model == 'OneChannel':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\swmm')
        swmm_to_gis_filename = 'onechan_trap.inp'
        gpkg_filename = 'onechan_trap_gpkg.gpkg'
        gis_to_swmm_filename = 'None'
        crs = 'EPSG:32760'
    elif model == 'OneChannel_storage':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneChannel\TUFLOW\swmm')
        swmm_to_gis_filename = 'None.inp'
        gpkg_filename = 'onechan_trap_store_gpkg.gpkg'
        gis_to_swmm_filename = 'onechan_trap_store.inp'
        crs = 'EPSG:32760'
    elif model == 'SF':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\SF\TUFLOW\SWMM')
        swmm_to_gis_filename = 'NotUsedSF.inp'
        gpkg_filename = 'SF_complete_outlets_streets_export_gpkg.gpkg'
        gis_to_swmm_filename = 'SF_complete_outlets_streets_003.inp'
    elif model == 'SF_results':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\SF\TUFLOW\results')
        swmm_to_gis_filename = 'SF_HPC10_SWMM___004_100yr_swmm.inp'
        gpkg_filename = 'SF_HPC10_SWMM___004_100yr_swmm.gpkg'
        gis_to_swmm_filename = 'notused.inp'
        crs = 'EPSG:26943'
    elif model == 'OneStreet':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneStreet\TUFLOW\swmm')
        swmm_to_gis_filename = 'NotUsedOneStreet.inp'
        gpkg_filename = 'OneStreet_gpkg.gpkg'
        gis_to_swmm_filename = 'OneStreet.inp'
    elif model == 'Mijoulan':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = '3M_Mijoulan - PRO2 100ans_1h.inp'
        gpkg_filename = 'Mijoulan_bmt.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        tags_to_filter = ['2D']
    elif model == 'Mijoulan_catchments':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'not_used.inp'
        gpkg_filename = 'mij_bmt_subcatch.gpkg'
        gis_to_swmm_filename = 'mij_bmt_subcatch.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        tags_to_filter = ['2D']
    elif model == 'Mijoulan_OnePipe':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = '3M_Mijoulan - PRO2 100ans_1h.inp'
        gpkg_filename = 'Mijoulan_bmt_single_pipe.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_single_pipe.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        tags_to_filter = ['2D']
    elif model == 'Mijoulan_003':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'NotUsed'
        gpkg_filename = 'Mijoulan_bmt_003.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_003.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        # tags_to_filter = ['2D']
    elif model == 'Mijoulan_003_losses':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'NotUsed'
        gpkg_filename = 'Mijoulan_bmt_003_losses.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_003_losses.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        # tags_to_filter = ['2D']
    elif model == 'Mijoulan_004_inlets':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'NotUsed'
        gpkg_filename = 'Mijoulan_bmt_004b_inlets.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_004b_inlets.inp'
        crs_filename = 'Mijoulan_crs.txt'
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()
        # tags_to_filter = ['2D']
    elif model == 'ExModels':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\ExampleModels\TUFLOW\results\EG15')
        swmm_to_gis_filename = 'EG15_SWMM_____004_swmm.inp'
        gpkg_filename = 'EG15_SWMM_____004_swmm.gpkg'
        gis_to_swmm_filename = 'notused_bmt.inp'
        crs = 'EPSG:32760'
        # crs_filename = 'Mijoulan_crs.txt'
        # with open(folder / crs_filename, 'r') as file:
        #    crs = file.read()
        # tags_to_filter = ['2D']
    elif model == 'ExModels_results':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\ExampleModels\TUFLOW\results\EG15')
        swmm_to_gis_filename = 'EG15_SWMM_FromESTRY___004_swmm.inp'
        gpkg_filename = 'EG15_SWMM_FromESTRY___004_swmm.gpkg'
        gis_to_swmm_filename = 'notused_bmt.inp'
        crs = 'EPSG:32760'
    elif model == 'ExModels_addverts':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\ExampleModels\TUFLOW\SWMM')
        swmm_to_gis_filename = 'not_used'
        gpkg_filename = 'EG15_addVerts.gpkg'
        gis_to_swmm_filename = 'EG15_addVerts.inp'
        crs = 'EPSG:32760'
        # crs_filename = 'Mijoulan_crs.txt'
        # with open(folder / crs_filename, 'r') as file:
        #    crs = file.read()
        # tags_to_filter = ['2D']
    elif model == 'ExModels_EstryOpenChans':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\ExampleModels\TUFLOW\SWMM')
        swmm_to_gis_filename = 'not_used'
        gpkg_filename = 'ExampleModel_culverts_only.gpkg'
        gis_to_swmm_filename = 'ExampleModel_culverts_only.inp'
        crs = 'EPSG:32760'

    elif model == 'Ruskin':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\Ruskin\TUFLOW\SWMM')
        swmm_to_gis_filename = 'Ruskin_004.inp'
        gpkg_filename = 'Ruskin_004.gpkg'
        gis_to_swmm_filename = 'Ruskin_004_mod.inp'
        crs = 'EPSG:27700'
    elif model == 'Ruskin_results':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\SWMM_from_ICM_Models\Ruskin\TUFLOW\results')
        swmm_to_gis_filename = 'rs_HPC05_SWMM___001_M5-60_swmm.inp'
        gpkg_filename = 'rs_HPC05_SWMM___001_M5-60_swmm.gpkg'
        gis_to_swmm_filename = 'notused.inp'
        crs = 'EPSG:27700'
    elif model == 'OneD1d':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\OneD1D_testing\TUFLOW\swmm')
        swmm_to_gis_filename = 'onechan_trap.inp'
        gpkg_filename = 'OneD1d.gpkg'
        gis_to_swmm_filename = 'OneD1d.inp'
        crs = 'EPSG:32760'
    elif model == 'Ventura-Arundell1':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Arundell')
        swmm_to_gis_filename = '20190317CityofVenturaMarketStOnlyNAVD88.inp'
        gpkg_filename = '20190317CityofVenturaMarketStOnlyNAVD88.gpkg'
        gis_to_swmm_filename = '20190317CityofVenturaMarketStOnlyNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-Arundell2':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Arundell')
        swmm_to_gis_filename = '20190320CityofVenturaArundell_MontalvoOnlyNAVD88.inp'
        gpkg_filename = '20190320CityofVenturaArundell_MontalvoOnlyNAVD88.gpkg'
        gis_to_swmm_filename = '20190320CityofVenturaArundell_MontalvoOnlyNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-AutoCenter':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Auto_Center')
        swmm_to_gis_filename = '20190329AutoCenterNAVD88.inp'
        gpkg_filename = '20190329AutoCenterNAVD88.gpkg'
        gis_to_swmm_filename = '20190329AutoCenterNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-Brown':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Brown_Test')
        swmm_to_gis_filename = 'BrownTest.inp'
        gpkg_filename = 'BrownTest.gpkg'
        gis_to_swmm_filename = 'BrownTest_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-Hall_Canyon':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Hall_Canyon')
        swmm_to_gis_filename = '20180426HallCynEx25Alt2_ModNODAMPEN.inp'
        gpkg_filename = '20180426HallCynEx25Alt2_ModNODAMPEN.gpkg'
        gis_to_swmm_filename = '20180426HallCynEx25Alt2_ModNODAMPEN_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-Harmon':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Harmon')
        swmm_to_gis_filename = '20180806HarmonOnlyNAVD88.inp'
        gpkg_filename = '20180806HarmonOnlyNAVD88.gpkg'
        gis_to_swmm_filename = '20180806HarmonOnlyNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-SuddenClarke':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\SuddenClarke_121218')
        swmm_to_gis_filename = '20181116Sudden_ClarkNAVD88.inp'
        gpkg_filename = '20181116Sudden_ClarkNAVD88.gpkg'
        gis_to_swmm_filename = '20181116Sudden_ClarkNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-West1':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Ventura_West')
        swmm_to_gis_filename = '20190514VenturaWest_RGNAVD88.inp'
        gpkg_filename = '20190514VenturaWest_RGNAVD88.gpkg'
        gis_to_swmm_filename = '20190514VenturaWest_RGNAVD88_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-West2':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM\Ventura_West')
        swmm_to_gis_filename = '20190514VenturaWest_RGNAVD88Gr2ft.inp'
        gpkg_filename = '20190514VenturaWest_RGNAVD88Gr2ft.gpkg'
        gis_to_swmm_filename = '20190514VenturaWest_RGNAVD88Gr2ft_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-SBW':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM')
        swmm_to_gis_filename = 'sb_w_pipes_wide.inp'
        gpkg_filename = 'sb_w_pipes_wide.gpkg'
        gpkg_to_swmm_filename = 'sb_w_pipes_wide_mod03.gpkg'
        gis_to_swmm_filename = 'sb_w_pipes_wide_mod03.inp'
        crs = 'EPSG:6424'
    elif model == 'Ventura-SBW-Losses':
        folder = Path(
            r'D:\models\TUFLOW\test_models\SWMM\internal\Ventura\TUFLOW_models\2023\TUFLOW\SWMM')
        swmm_to_gis_filename = 'None.inp'
        gpkg_filename = 'None.gpkg'
        gpkg_to_swmm_filename = 'sb_w_pipe_losses_mod.gpkg'
        gis_to_swmm_filename = 'sb_w_pipe_losses_mod.inp'
        crs = 'EPSG:6424'
    elif model == 'Mijoulan_005_inlets':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'Mijoulan_bmt_004_inlets.inp'
        gpkg_filename = 'Mijoulan_bmt_005_inlets.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_005_inlets.inp'
        crs_filename = 'Mijoulan_crs.txt'
    elif model == 'Mijoulan_005b_inlets':
        folder = Path(r'D:\models\TUFLOW\test_models\SWMM\internal\PCSWMM_France\BMT\TUFLOW\swmm')
        swmm_to_gis_filename = 'Mijoulan_bmt_004b_inlets.inp'
        gpkg_filename = 'Mijoulan_bmt_005b_inlets.gpkg'
        gis_to_swmm_filename = 'Mijoulan_bmt_005b_inlets.inp'
        crs_filename = 'Mijoulan_crs.txt'
    else:
        raise ValueError("Not setup")

    if crs_filename:
        with open(folder / crs_filename, 'r') as file:
            crs = file.read()

    operation = ['ToGIS', 'ToSWMM', 'AddSection'][0]

    if operation == 'ToGIS':
        swmm_to_gpkg(folder / swmm_to_gis_filename,
                     folder / gpkg_filename,
                     crs,
                     tags_to_filter)
    if operation == 'ToSWMM':
        from_filename = gpkg_to_swmm_filename if gpkg_to_swmm_filename else gpkg_filename
        gis_to_swmm(folder / from_filename,
                    folder / gis_to_swmm_filename)
