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

from tuflow.tuflow_swmm.gis_list_layers import get_gis_layers
from tuflow.tuflow_swmm.layer_util import increment_layer
from tuflow.tuflow_swmm.swmm_processing_feedback import ScreenProcessingFeedback
from tuflow.tuflow_swmm.xpswmm_gis_cleanup import bc_layer_processing
from tuflow.tuflow_swmm.xpswmm_xpx_to_gpkg import xpx_to_gpkg


def parse_control_line(control_line: str) -> (str, str):
    line_vals = control_line.split('==')
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


def get_bc_filenames_and_paths(tcf_path, feedback):
    bc_abs_paths_and_layernames = []

    tcf_spatial_database = None

    with open(tcf_path, 'r') as tcf_file:
        for line in tcf_file:
            command, value = parse_control_line(line)

            if command.lower() == 'bc control file':
                tbc_filename = value
            elif command.lower() == 'spatial database':
                tcf_spatial_database = Path(value)

    tbc_spatial_database = None
    if tbc_filename == '':
        feedback.reportError('BC Control file not found in tcf.', fatalError=False)
        return bc_abs_paths_and_layernames
    tbc_path = (tcf_path.parent / tbc_filename).resolve()
    if not tbc_path.exists():
        feedback.reportError(f'Unable to find TUFLOW BC Control file. Make sure the file exists and is correctly '
                             f'referrenced in the TCF file.\nTBC: {tbc_path}.',
                             fatalError=False)
        return bc_abs_paths_and_layernames
    try:
        with open(tbc_path, 'r') as tbc_file:
            for line in tbc_file:
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

                        bc_abs_paths_and_layernames.append((bc_filename_full, bc_layer))
    except Exception as e:
        feedback.reportError(f'Unknown error parsing tbc file and processing BC layers. Aborted: {str(e)}')

    return bc_abs_paths_and_layernames


def convert_xpswmm(output_folder_1donly: str,
                   xpx_filename: str,
                   tcf_filename: str,
                   swmm_prefix: str,
                   solution_scheme: str,
                   hardware: str,
                   default_event_name: str,
                   bc_offset_width: float,
                   bc_offset_dist: float,
                   gis_layers_filename: str,
                   crs: str, feedback=ScreenProcessingFeedback()):
    if tcf_filename is None:
        tcf_path = None
        tuflow_folder = None
        swmm_folder = Path(output_folder_1donly)
    else:
        tcf_path = Path(tcf_filename)
        tuflow_folder = Path(tcf_filename).parent.parent
        swmm_folder = tuflow_folder / 'model\\swmm'

    swmm_folder.mkdir(exist_ok=True, parents=True)
    swmm_inp_gpkg_filename = swmm_folder / f'{swmm_prefix}_001.gpkg'
    swmm_inp_filename = swmm_folder / f'{swmm_prefix}_001.inp'
    swmm_iu_filename = swmm_folder / f'{swmm_prefix}_iu_001.gpkg'
    swmm_messages_filename = str(swmm_folder / f'{swmm_prefix}_convert_messages.gpkg')

    tscf_filename = None
    tef_filename = None

    if tuflow_folder is not None:
        tscf_filename = tuflow_folder / f'model\\{swmm_prefix}_001.tscf'
        tef_filename = tuflow_folder / f'runs\\tuflow_events.tef'

        bc_dbase_filename = get_bc_dbase_filename(tcf_filename, feedback)
    else:
        bc_dbase_filename = swmm_folder / f'bc_dbase\\bc_dbase.csv'

    bc_abs_paths_and_layernames = []
    bc_out_paths_and_layernames = []
    if tcf_path is not None:
        bc_abs_paths_and_layernames = get_bc_filenames_and_paths(tcf_path, feedback)

        bc_out_paths_and_layernames = [increment_layer(f, l) for f, l in bc_abs_paths_and_layernames]

    swmm_info = xpx_to_gpkg(xpx_filename,
                            swmm_inp_gpkg_filename,
                            bc_abs_paths_and_layernames,
                            bc_out_paths_and_layernames,
                            bc_offset_dist,
                            bc_offset_width,
                            gis_layers_filename,
                            swmm_iu_filename,
                            swmm_messages_filename,
                            str(bc_dbase_filename),
                            default_event_name,
                            tef_filename,
                            crs,
                            feedback)

    if tscf_filename is None:
        return

    with open(tscf_filename, 'w') as tscf_file:
        tscf_file.write(f'Read SWMM == .\\swmm\\{swmm_inp_filename.name}\n\n')

        # If there are no inlets this file will not exist
        if Path(swmm_iu_filename).exists():
            tscf_file.write(f'Read GIS SWMM Inlet Usage == .\\swmm\\{swmm_iu_filename.name} >> inlet_usage_001\n\n')

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
        'Read GIS XP WLL',
        'Read GIS XP NETWORK',
    ]

    tcf_to_remove = [
        'Write Check Files',
        'Output Folder',
        'Log Folder',
    ]
    # Need to add event
    orig_filename = tcf_filename
    tcf_path = tcf_path.with_stem(f'{tcf_path.stem}_~e1~')

    tbc_filename = ''

    tcf_spatial_database = None

    with open(tcf_path, 'w') as tcf_file, open(orig_filename, 'r') as orig_file:
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

    # Remove the original tcf file
    Path(orig_filename).unlink()

    tbc_spatial_database = None
    if tbc_filename == '':
        feedback.reportError('BC Control file not found in tcf. No BC modifications were made.',
                             fatalError=False)
    else:
        tbc_path = (tcf_path.parent / tbc_filename).resolve()
        if not tbc_path.exists():
            feedback.reportError(f'Unable to find TUFLOW BC Control file. Make sure the file exists and is correctly '
                                 f'referrenced in the TCF file.\nTBC: {tbc_path}.',
                                 fatalError=False)
        else:
            try:
                # make backup copy
                tbc_orig_file = tbc_path.with_stem(tbc_path.stem + '_orig')
                shutil.copy(str(tbc_path), str(tbc_orig_file))

                feedback.pushInfo(f'Processing TBC file: {tbc_path}')
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

                                if Path(bc_out_filename).is_absolute():
                                    bc_out_filename_full = bc_out_filename
                                else:
                                    bc_out_filename_full = tbc_path.parent / bc_out_filename

                                bc_out_filename, bc_out_layername = increment_layer(bc_out_filename, bc_layer)

                                if bc_layer_processing(bc_filename_full,
                                                       bc_layer,
                                                       str(swmm_inp_gpkg_filename),
                                                       bc_out_filename_full,
                                                       bc_out_layername):

                                    if spatial_database:
                                        # do not need a folder
                                        tbc_file.write(f'Read GIS BC == {bc_out_layername}\n')
                                    elif bc_out_layername is not None:
                                        tbc_file.write(f'Read GIS BC == {bc_out_filename} >> {bc_out_layername}\n')
                                    else:
                                        tbc_file.write(f'Read GIS BC == {bc_out_filename}\n')
                                else:
                                    # file not used do not write to tbc file
                                    pass
                        else:
                            # Not one of the intercepted commands above echo to new file
                            tbc_file.write(line)
                    # Append reference to new bc connection layers if they were created
                    if gis_layers_filename is not None:
                        gis_layers_filename = Path(gis_layers_filename)
                        if '2d_bc_swmm_connections' in get_gis_layers(gis_layers_filename):
                            tbc_file.write('\n! Add SWMM 1D nodal HX/SX connections\n')
                            relative_filename = gis_layers_filename.relative_to(tbc_path.parent.resolve())
                            tbc_file.write(f'Read GIS BC == {relative_filename} >> 2d_bc_swmm_connections\n')
            except Exception as e:
                feedback.reportError(f'Unknown error parsing tbc file and processing BC layers. Aborted: {str(e)}')


if __name__ == "__main__":
    tcf_folder_to_copy = Path(r"D:\support\TSC240873\190702_Model\model_convert_gpkg")
    out_folder = tcf_folder_to_copy.with_name(tcf_folder_to_copy.name + '_001')
    if out_folder.exists():
        shutil.rmtree(out_folder)
    shutil.copytree(tcf_folder_to_copy, out_folder)

    xpx_filename = r"D:\support\TSC240873\190702_Model\02-Existing\EX_US77_100yr.xpx"
    tcf_filename = out_folder / 'runs\\EX_US77_100yr.tcf'
    swmm_prefix = 'us77'
    crs_ex = (r'PROJCRS["unnamed",BASEGEOGCRS["Unknown datum based upon the GRS 1980 ellipsoid",DATUM["Not specified ('
              r'based on GRS 1980 ellipsoid)",ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1]]],'
              r'PRIMEM["Greenwich",0,ANGLEUNIT["degree",0.0174532925199433]],ID["EPSG",4019]],CONVERSION["unknown",'
              r'METHOD["Lambert Conic Conformal (2SP)",ID["EPSG",9802]],PARAMETER["Latitude of false origin",'
              r'25.6666666666667,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8821]],PARAMETER["Longitude of '
              r'false origin",-98.5,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8822]],PARAMETER["Latitude of '
              r'1st standard parallel",26.1666666666667,ANGLEUNIT["degree",0.0174532925199433],ID["EPSG",8823]],'
              r'PARAMETER["Latitude of 2nd standard parallel",27.8333333333333,ANGLEUNIT["degree",'
              r'0.0174532925199433],ID["EPSG",8824]],PARAMETER["Easting at false origin",984250,LENGTHUNIT["Foot_US",'
              r'0.304800609601219],ID["EPSG",8826]],PARAMETER["Northing at false origin",16404166.6666667,LENGTHUNIT['
              r'"Foot_US",0.304800609601219],ID["EPSG",8827]]],CS[Cartesian,2],AXIS["(E)",east,ORDER[1],LENGTHUNIT['
              r'"Foot_US",0.304800609601219]],AXIS["(N)",north,ORDER[2],LENGTHUNIT["Foot_US",0.304800609601219]]]')
    event_name_to_use = 'event1'

    gis_layers_filename = out_folder / r"model\gis\us77_add_gis_layers.gpkg"
    output_folder_1donly = ''  # not used

    convert_xpswmm(output_folder_1donly,
                   xpx_filename,
                   str(tcf_filename),
                   swmm_prefix,
                   'HPC',
                   'GPU',
                   event_name_to_use,
                   10,
                   1.0,
                   str(gis_layers_filename),
                   crs_ex)
