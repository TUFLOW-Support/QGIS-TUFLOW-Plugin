import fiona
import geopandas as gpd
from itertools import chain
import pandas as pd
from pathlib import Path
from tuflow.tuflow_swmm.gis_to_swmm import gis_to_swmm
from tuflow.tuflow_swmm.swmm_io import write_tuflow_version
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.swmm_sections import primary_node_sections, primary_link_sections


def extract_scenarios(gpkg_filenames, scenario_names, output_folder, output_prefix,
                      output_control_file_lines,
                      feedback=ScreenProcessingFeedback()):
    feedback.pushInfo(f'Extracting scenarios from SWMM GPKG.')
    feedback.pushInfo(f'\n\tScenario, filename')
    scenarios_and_paths = [f'{x} {y}' for x, y in zip(scenario_names, gpkg_filenames)]
    feedback.pushInfo(f'\t{"\n\t".join(scenarios_and_paths)}')

    if len(scenarios_and_paths) < 2:
        feedback.reportError(f'At least two scenarios are required to extract scenarios.', True)
        raise ValueError('At least two scenarios are required to extract scenarios.')

    output_path = Path(output_folder)
    output_path.mkdir(exist_ok=True, parents=True)

    output_filenames = [output_path / f'{output_prefix}_{s}.gpkg' for s in scenario_names]

    common_filename = output_path / f'{output_prefix}_Common.gpkg'

    for output_filename in chain(output_filenames, [common_filename]):
        Path(output_filename).unlink(missing_ok=True)

    section_tables = [f'Nodes--{ns}' for ns in primary_node_sections] + \
                     [f'Links--{ls}' for ls in primary_link_sections]

    # Handle the node tables
    for section_table in section_tables:
        # read the dataframe for each model
        common_entries = []
        gdfs_section = []

        feedback.pushInfo(f'\nProcessing {section_table}')

        for scenario, scenario_filename in zip(scenario_names, gpkg_filenames):
            if section_table in fiona.listlayers(scenario_filename):
                gdfs_section.append(gpd.read_file(scenario_filename, layer=section_table))
            else:
                gdfs_section.append(None)

        common_entries = set()

        valid_sections = [x is not None for x in gdfs_section]
        if not any(valid_sections):
            feedback.pushInfo('\tNot used in any scenarios. Skipping...')
            continue

        if all(valid_sections):
            feedback.pushInfo('\tUsed in all scenarios')

            item_names = [set(x['Name']) for x in gdfs_section]

            common_entries = set.intersection(*item_names)

        else:
            feedback.pushInfo('\tUsed in some scenarios')

            # No common entries - nothing needed

        gdf_common = None
        if len(common_entries) > 0:
            # Use values from first geopackage
            gdf_common = gdfs_section[0][gdfs_section[0]['Name'].isin(common_entries)]
            # print(gdf_common)

            feedback.pushInfo(f'Writing {section_table} to {common_filename} ({len(gdf_common)})')
            gdf_common.to_file(common_filename, layer=section_table, driver='GPKG')

        # Write to the individual files
        for scenario, scenario_filename, gdf_section in zip(scenario_names, output_filenames, gdfs_section):
            # scenario_entries = set(gdf_section['Name']) - common_entries

            # Add any rows that have different values than the common tables
            if gdf_common is not None:
                gdf_common_plus_scenario = pd.concat([gdf_common, gdf_section], ignore_index=True)
            else:
                gdf_common_plus_scenario = gdf_section
            gdf_modified = gdf_common_plus_scenario.drop_duplicates(ignore_index=True, keep=False)
            # Now drop the first item from each modified row
            gdf_modified = gdf_modified.drop_duplicates(subset=['Name'], keep='last')
            print(f'Number of modified rows: {len(gdf_modified)}')

            #if len(scenario_entries) + len(gdf_modified) > 0:
            if len(gdf_modified) > 0:
                #gdf_section = gdf_section[gdf_section['Name'].isin(scenario_entries)]
                #gdf_section = pd.concat([gdf_section, gdf_modified], ignore_index=True)
                feedback.pushInfo(f'Writing {section_table} to {scenario_filename} ({len(gdf_modified)})')
                gdf_modified.to_file(scenario_filename, layer=section_table, driver='GPKG')

    # Handle non-node and conduit layers
    generic_tables = set(fiona.listlayers(gpkg_filenames[0])) - set(section_tables)
    feedback.pushInfo(f'\nCopying generic tables to common file:')

    for generic_table in generic_tables:
        gdf_generic = gpd.read_file(gpkg_filenames[0], layer=generic_table)
        gdf_generic.to_file(common_filename, layer=generic_table, driver='GPKG')

    # Create the SWMM inp files
    feedback.pushInfo('\n\nConverting to EPA SWMM inp files:')

    feedback.pushInfo(f'\nConverting common file: {common_filename}')
    gis_to_swmm(common_filename, common_filename.with_suffix('.inp'))

    for scenario, output_filename in zip(scenario_names, output_filenames):
        # It is possible that the scenario doesn't have anything different from common
        if output_filename.exists():
            feedback.pushInfo(f'\nConverting {output_filename}.\n')
            gis_to_swmm(output_filename, output_filename.with_suffix('.inp'), feedback)
            write_tuflow_version(output_filename)
        else:
            feedback.pushInfo(f'\nSkipping {output_filename} (no unique components).\n')

    # Do messages for if statements
    tscf_text = f'Read SWMM == SWMM\\{common_filename.with_suffix('.inp').name}\n'

    if_block_started = False
    for scenario, output_filename in zip(scenario_names, output_filenames):
        # It is possible that the scenario doesn't have anything different from common
        if output_filename.exists():
            if not if_block_started:
                if_block_started = True
                tscf_text = tscf_text + f'\nIf Scenario == {scenario}\n'
            else:
                tscf_text = tscf_text + f'Else If Scenario == {scenario}\n'
            tscf_text = tscf_text + f'    Read SWMM == SWMM\\{output_filename.with_suffix('.inp').name}\n'
    tscf_text = tscf_text + 'End If\n'

    feedback.pushInfo('\n\nTUFLOW-SWMM Control File Lines:\n')
    feedback.pushInfo(tscf_text)

    with open(output_control_file_lines, 'w') as out_file:
        out_file.write(tscf_text)

if __name__ == '__main__':
    gpkg_filenames = [
        r"D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_26\TUFLOW\model\swmm\to1b_001.gpkg",
        r"D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_26\scenario_Alt01_OU\to1b_001.gpkg",
        r"D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_26\scenario_Alt02_OU_NT\to1b_001.gpkg",
        r"D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_26\scenario_Alt03_All\to1b_001.gpkg",
    ]
    scenario_names = [
        'Base',
        'Alt01_OU',
        'Alt02_OU_NT',
        'Alt03_All',
    ]

    output_folder = r'D:\models\TUFLOW\test_models\SWMM\WoodardCurran\bmt_2024_07_26\scenarios_out\\'
    output_prefix = 'TO1B'

    output_control_file_lines = Path(output_folder) / 'control_file_lines.txt'

    extract_scenarios(gpkg_filenames, scenario_names, output_folder, output_prefix, output_control_file_lines)
