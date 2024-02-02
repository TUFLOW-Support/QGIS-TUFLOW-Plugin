import os

os.environ['USE_PYGEOS'] = '0'

import pandas as pd
from pathlib import Path

from tuflow_swmm.unused.swmm_to_gis import swmm_to_gpkg
from tuflow_swmm.unused.gis_to_swmm import gis_to_swmm

if __name__ == "__main__":
    pd.set_option('display.max_columns', 500)
    # pd.set_option('display.max_rows', 500)
    pd.set_option('display.width', 200)

    tags_to_filter = None

    model = ['SF',
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
             ][-1]

    if model == 'SF':
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
    else:
        raise ValueError("Not setup")

    operation = ['ToGIS', 'ToSWMM', 'AddSection'][1]

    if operation == 'ToGIS':
        swmm_to_gpkg(folder / swmm_to_gis_filename,
                     folder / gpkg_filename,
                     crs,
                     tags_to_filter)
    if operation == 'ToSWMM':
        gis_to_swmm(folder / gpkg_filename,
                    folder / gis_to_swmm_filename)
