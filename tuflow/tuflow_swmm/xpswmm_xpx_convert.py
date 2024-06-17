"""
Converts an XPX file and modifies a converted tcf file to add the SWMM information, including:
1. Creates input files from the xpx file
    a. SWMM inp file (and gpkg)
    b. Inlet usage file
    c. Messages file for conversion
2. Creates the TUFLOW-SWMM control file ..\\model\\swmm folder and fills it in
3. Modifies the TCF file (leaves copy of original)
    a. Adds tscf, start/end time, and other stuff
    b. Comment out commands not used for TUFLOW-SWMM or no longer recommended
4. Modifies the tbc file (leaves copy of original)
    a.  Snaps any bc polyline files to the SWMM node layers
"""
from pathlib import Path
import re
import shutil

from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.xpswmm_gis_cleanup import bc_layer_processing
from tuflow.tuflow_swmm.xpswmm_xpx_to_gpkg import xpx_to_gpkg


def parse_control_line(control_line: str) -> (str, str):
    line_vals = control_line.split('==')
    command = ''
    value = ''
    if len(line_vals) > 1:
        command, value = line_vals[0], line_vals[1]
    else:
        command = line_vals[0]
    command = command.strip()
    value = value.strip()

    return command, value


def get_bc_dbase_filename(tcf_filename: str, feedback) -> Path:
    with open(tcf_filename, 'r') as tcf_file:
        for line in tcf_file:
            command, value = parse_control_line(line)

            if command.strip().lower() == 'bc database':
                bc_dbase_path = Path(value)
                if not bc_dbase_path.is_absolute():
                    bc_dbase_path = Path(tcf_filename).parent / bc_dbase_path
                    bc_dbase_path = bc_dbase_path.resolve()

                feedback.pushInfo(f'Appending to BC database: {bc_dbase_path}')
                return bc_dbase_path

    # if we get here we didn't find anything
    bc_dbase_path = Path(tcf_filename) / '..\\bc_dbase\\bc_dbase.csv'
    bc_dbase_path = bc_dbase_path.resolve()
    bc_dbase_path.parent.mkdir(parents=True, exist_ok=True)
    feedback.pushWarning(f'No BC Database Found. Creating: {bc_dbase_path}')
    return bc_dbase_path


def convert_xpswmm(
        xpx_filename: str,
        tcf_filename: str,
        swmm_prefix: str,
        solution_scheme: str,
        hardware: str,
        default_event_name: str,
        crs: str,
        feedback=ScreenProcessingFeedback(),
):
    skip_xpx_to_gpkg = False

    tcf_path = Path(tcf_filename)
    tuflow_folder = Path(tcf_filename).parent.parent
    swmm_folder = tuflow_folder / 'model\\swmm'
    swmm_folder.mkdir(exist_ok=True, parents=True)

    swmm_inp_gpkg_filename = swmm_folder / f'{swmm_prefix}_001.gpkg'
    swmm_inp_filename = swmm_folder / f'{swmm_prefix}_001.inp'
    swmm_iu_filename = swmm_folder / f'{swmm_prefix}_iu_001.gpkg'
    swmm_messages_filename = str(swmm_folder / f'{swmm_prefix}_convert_messages.gpkg')
    tscf_filename = tuflow_folder / f'model\\{swmm_prefix}_001.tscf'
    tef_filename = tuflow_folder / f'runs\\tuflow_events.tef'

    bc_dbase_filename = get_bc_dbase_filename(tcf_filename, feedback)

    swmm_info = {}
    if not skip_xpx_to_gpkg:
        swmm_info = xpx_to_gpkg(xpx_filename,
                                swmm_inp_gpkg_filename,
                                swmm_iu_filename,
                                swmm_messages_filename,
                                str(bc_dbase_filename),
                                default_event_name,
                                str(tef_filename),
                                crs)

    with open(tscf_filename, 'w') as tscf_file:
        tscf_file.write(f'Read SWMM == .\\swmm\\{swmm_inp_filename.name}\n\n')

        tscf_file.write(f'Read GIS SWMM Inlet Usage == .\\swmm\\{swmm_iu_filename.name} >> inlet_usage\n\n')

        if 'Timeseries_curves' in swmm_info:
            tscf_file.write(f'Read BC Timeseries == {" | ".join(swmm_info["Timeseries_curves"])}\n')

    tcf_to_comment = [
        'Check MI Save Date',
        'Mass Balance Output Interval(s)',
        'MI Projection',
        'CSV Time',
        'MI Projection Check',
        'Viscosity Formulation',
        'Timestep (s)',
        'Viscosity Coefficient',
        'Cell Wet / Dry Depth',
        'SX ZC Check',
        'Read GIS XP Nodes',
        'SX Storage Approach',
        'Simulations Log Folder',
        'HX ZC Check',
        'Store Maximums and Minimums',
        'Mass Balance Corrector',
        'Mass Balance Output',
    ]

    tcf_to_remove = [
        'Write Check Files',
        'Output Folder',
        'Log Folder',
    ]
    # Need to add event
    orig_file = tcf_filename
    tcf_path = tcf_path.with_stem(f'{tcf_path.stem}_~e1~')

    tbc_filename = ''

    tcf_spatial_database = None

    with open(tcf_path, 'w') as tcf_file, open(orig_file, 'r') as orig_file:
        for line in orig_file:
            command, value = parse_control_line(line)

            if command.lower() == 'bc control file':
                tbc_filename = value
            elif command.lower() == 'spatial database':
                tcf_spatial_database = Path(value)

            # Comment out commands to not use
            for to_comment in tcf_to_comment:
                if command.find(to_comment) != -1:
                    line = '! ' + line

            for to_remove in tcf_to_remove:
                if command.find(to_remove) != -1:
                    line = None

            if line is not None:
                tcf_file.write(line)

        # Add new commands
        tcf_file.write(f'\n\n')
        tcf_file.write(f'Event File == {tef_filename.name}\n')
        tcf_file.write(f'Solution Scheme == {solution_scheme}\n')
        tcf_file.write(f'Hardware == {hardware}\n')
        tcf_file.write('Write Check Files == ..\\check\\\n')
        tcf_file.write('Output Folder == ..\\results\\\n')
        tcf_file.write('Log Folder == log\n')
        tcf_file.write(f'\n')
        tcf_file.write('GIS Format == GPKG\n')
        tcf_file.write(f'SWMM Control File == ..\\model\\{tscf_filename.name}\n')

        num_hours = 0.0
        if 'start_date' not in swmm_info or 'end_date' not in swmm_info:
            feedback.reportError('Time information not parsed from xpx. Add time information')
        else:
            num_hours = (swmm_info['end_date'] - swmm_info['start_date']).total_seconds() / 3600.

        tcf_file.write(f'Start Time == 0\n')
        tcf_file.write(f'End Time == {num_hours}\n')

        if 'start_date' in swmm_info:
            start_date_text = swmm_info['start_date'].strftime('%Y-%m-%d %H:%M')
            tcf_file.write(f'NetCDF Output Start Date == {start_date_text}\n')

    re_version = re.compile('.*([0-9]{3}).*')

    tbc_spatial_database = None
    if tbc_filename == '':
        feedback.reportError('BC Control file not found in tcf. No BC modifications were made.')
    else:
        # make backup copy
        tbc_path = tcf_path.parent / tbc_filename
        tbc_orig_file = tbc_path.with_stem(tbc_path.stem + '_orig')
        shutil.copy(str(tbc_path), str(tbc_orig_file))

        with open(tbc_path, 'w') as tbc_file, open(tbc_orig_file, 'r') as orig_file:
            for line in orig_file:
                command, value = parse_control_line(line)

                if command.lower() == 'spatial database':
                    tbc_spatial_database = Path(value)
                    tbc_file.write(line)
                elif command.lower() == 'read gis bc':
                    bc_filenames = [x.strip() for x in value.split('|')]

                    # If a spatial database has been defined (gpkg) get files and layers
                    bc_files_layers = []  # tuple (filename, layername)
                    spatial_database = None
                    if tbc_spatial_database is not None:
                        if Path(tbc_spatial_database).is_absolute():
                            spatial_database = tbc_spatial_database
                        else:
                            spatial_database = tbc_path.parent / tbc_spatial_database
                    elif tcf_spatial_database is not None:
                        if Path(tcf_spatial_database).is_absolute():
                            spatial_database = tcf_spatial_database
                        else:
                            spatial_database = tcf_path.parent / tcf_spatial_database

                    if spatial_database is not None and spatial_database.suffix.lower() == '.gpkg':
                        bc_files_layers = [(None, x) for x in bc_filenames]
                    else:
                        for bc_filename in bc_filenames:
                            # Specified filenames
                            if len(bc_filename.split('>>')) > 1:
                                filename, layers = [x.strip() for x in bc_filename.split('>>')]
                            else:
                                filename = bc_filename
                                layers = None

                            if layers is not None:
                                layers = [x.strip() for x in layers.split('&&')]
                                bc_files_layers = bc_files_layers + [(filename, x) for x in layers]
                            else:
                                bc_files_layers = bc_files_layers + [(filename, None)]

                    for (bc_filename, bc_layer) in bc_files_layers:
                        if bc_filename is None:
                            bc_filename = spatial_database

                        if not Path(bc_filename).is_absolute():
                            bc_filename_full = tbc_path.parent / bc_filename
                        else:
                            bc_filename_full = bc_filename

                        bc_out_filename = bc_filename
                        bc_out_layername = bc_layer

                        if Path(bc_out_filename).is_absolute():
                            bc_out_filename_full = bc_out_filename
                        else:
                            bc_out_filename_full = tbc_path.parent / bc_out_filename

                        if bc_layer is None:
                            # increment the filename
                            version = 2
                            re_version_match = re.match(re_version, Path(bc_filename).stem)
                            if re_version_match:
                                version = int(re_version_match.groups()[0])
                                Path(bc_out_filename).with_stem(re.sub('[0-9]{3}', f'{version + 1:03}',
                                                                       Path(bc_filename).stem))
                            else:
                                bc_out_filename = bc_filename + '_002'
                        else:
                            # increment the layername
                            re_version_match = re.match(re_version, bc_layer)
                            if re_version_match:
                                version = int(re_version_match.groups()[0])
                                bc_out_layername = re.sub('[0-9]{3}', f'{version + 1:03}', bc_layer)
                            else:
                                # Tack on a 002 at the end
                                bc_out_layername = bc_layer + '_002'

                        if bc_layer_processing(bc_filename_full,
                                               bc_layer,
                                               str(swmm_inp_gpkg_filename),
                                               bc_out_filename_full,
                                               bc_out_layername):

                            if spatial_database:
                                # do not need a folder
                                tbc_file.write(f'Read GIS BC == {bc_out_layername}')
                            elif bc_out_layername is not None:
                                tbc_file.write(f'Read GIS BC == {bc_out_filename} >> {bc_out_layername}')
                            else:
                                tbc_file.write(f'Read GIS BC == {bc_out_filename}')
                        else:
                            # file not used do not write to tbc file
                            pass
                else:
                    # Not one of the intercepted commands above echo to new file
                    tbc_file.write(line)


if __name__ == "__main__":
    xpx_filename = r"D:\models\TUFLOW\test_models\SWMM\wikitutorial\20240415\xpswmm_convert\XPSWMM_to_TUFLOW_Model_Conversion\XPSWMM\1D2D_Urban_001.xpx"
    tcf_filename = (r"D:\models\TUFLOW\test_models\SWMM\wikitutorial\20240415\xpswmm_convert"
                    r"\XPSWMM_to_TUFLOW_Model_Conversion\test_convert\convert_all_in_one_gpkg\runs\1D2D_Urban_001.tcf")
    swmm_prefix = 'urban'
    crs_ex = 'EPSG:32760'
    event_name_to_use = 'event1'

    convert_xpswmm(xpx_filename,
                   tcf_filename,
                   swmm_prefix,
                   'HPC',
                   'GPU',
                   event_name_to_use,
                   crs_ex)