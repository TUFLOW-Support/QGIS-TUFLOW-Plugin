import json

from qgis.PyQt.QtCore import QCoreApplication
from qgis._core import QgsProcessingParameterBoolean, QgsProcessingParameterString, QgsProcessingModelGroupBox, \
    QgsProcessingParameterCrs
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
import subprocess
import sys
import time
import re
import os
from pathlib import Path

from ..gui.processing.processsing_param_conv_tuf_model_format_dir_settings import \
    ProcessingParameterConvTufModelDirSettings

CONTROL_FILES = [
    'GEOMETRY CONTROL FILE', 'BC CONTROL FILE', 'ESTRY CONTROL FILE', 'EVENT FILE', 'READ FILE',
    'RAINFALL CONTROL FILE', 'EXTERNAL STRESS FILE', 'QUADTREE CONTROL FILE', 'AD CONTROL FILE'
]


def strip_command(text):
    t = text
    c, v, comment = None, None, ''
    if t.strip() and not t[0] in ('!', '#'):
        if '!' in t or '#' in t:
            i = t.index('!') if '!' in t else 9e29
            j = t.index('#') if '#' in t else 9e29
            comment_index = k = min(i, j)
            t, comment = t[:k], t[k:].strip()
        if '==' in t:
            c, v = t.split('==', 1)
            v = v.strip()
        else:
            c, v = t, None
        if c.strip():
            prefix = re.split(r'[a-z]', c, flags=re.IGNORECASE)[0]
        c = c.strip().upper()

    return c, v


def globify(text):
    wildcards = [r'(<<.{1,}?>>)']
    new_text = text
    for wc in wildcards:
        new_text = re.sub(wc, '*', new_text, flags=re.IGNORECASE)
    if re.findall(re.escape(r'**'), new_text):
        new_text = re.sub(re.escape(r'**'), '*', new_text)

    return new_text


def count_lines(file, write_empty=False):
    from ..convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.empty_files import TuflowEmptyFiles
    from ..convert_tuflow_model_gis_format.conv_tf_gis_format.helpers.file import TuflowPath

    line_count = 0
    if os.path.exists(file):
        with open(file, 'r', errors='ignore') as f:
            for line in f:
                if line.strip():
                    line_count += 1
                command, value = strip_command(line)
                if command in CONTROL_FILES:
                    line_count += 1
                    if value.upper() == 'AUTO' or command.upper() == 'ESTRY CONTROL FILE AUTO':
                        value = '{0}.ecf'.format(os.path.splitext(os.path.basename(value))[0])
                    value = (TuflowPath(file).parent / value).resolve()
                    value = os.path.relpath(value, Path(file).parent.resolve())
                    value = globify(value)
                    for cf in Path(file).parent.glob(value):
                        line_count += count_lines(cf)

    if write_empty:
        line_count += TuflowEmptyFiles.empty_count()

    return line_count


GIS_FORMAT = {0: 'GPKG', 1: 'SHP', 2: 'MIF'}
GRID_FORMAT = {0: 'TIF', 1: 'GPKG', 2: 'FLT', 3: 'ASC'}
OP = {0: 'SEPARATE', 1: 'CF1', 2: 'CF2', 3: 'TCF'}


class ConvertTuflowModelGisFormat(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('tcf', 'TCF', behavior=QgsProcessingParameterFile.File,
                                                     fileFilter='TCF (*.tcf *.TCF)', defaultValue=None))
        self.addParameter(QgsProcessingParameterEnum('outputvectorformat', 'Output Vector Format',
                                                     options=['GPKG', 'SHP', 'MIF'], allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('outputrasterformat', 'Output Raster Format',
                                                     options=['GTIFF', 'GPKG', 'FLT', 'ASC'], allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('outputprofile', 'Output Profile',
                                                     options=['SEPARATE', 'GROUP BY CONTROL FILE 1',
                                                              'GROUP BY CONTROL FILE 2', 'ALL IN ONE'],
                                                     allowMultiple=False, defaultValue=[0]))
        self.addParameter(QgsProcessingParameterFile('outputfolder', 'Output Folder', optional=True,
                                                     behavior=QgsProcessingParameterFile.Folder,
                                                     fileFilter='All files (*.*)', defaultValue=None))
        param = QgsProcessingParameterFile('rootfolder', 'Root Folder', optional=True,
                                           behavior=QgsProcessingParameterFile.Folder, fileFilter='All files (*.*)',
                                           defaultValue=None)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        param = QgsProcessingParameterBoolean('usescenarios', 'Restrict Conversion by Scenarios')
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterString('scenarios',
                                             'Scenarios (list as you would with TUFLOW e.g. -s BASE -s 5m -e Q100)',
                                             optional=True)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterString('gpkg_name', 'Output GPKG Name (for grouped profiles)', optional=True)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterBoolean('write_empties', 'Write Empty Files')
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterString('empty_directory', 'Write Empty Files Relative Directory ',
                                             optional=True)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterCrs('output_crs', 'Output CRS', optional=True)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)
        param = QgsProcessingParameterBoolean('tuflow_dir_struct', 'Force TUFLOW Directory Structure')
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        struct_json = Path(
            __file__).parent.parent / 'convert_tuflow_model_gis_format' / 'conv_tf_gis_format' / 'data' / 'dir_relationships.json'
        with struct_json.open() as fo:
            default_struct = json.load(fo)
        param = ProcessingParameterConvTufModelDirSettings('tuflow_dir_struct_settings',
                                                           'TUFLOW Directory Structure Settings',
                                                           optional=True,
                                                           default=default_struct)
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

        param = QgsProcessingParameterBoolean('explode_multipart', 'Explode MultiPart Features')
        param.setFlags(param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        line_count = count_lines(parameters['tcf'], parameters['write_empties']) + 3

        feedback = QgsProcessingMultiStepFeedback(line_count, model_feedback)
        feedback.pushInfo('line count: {0}'.format(line_count))

        # params
        tcf = parameters['tcf']
        gis = GIS_FORMAT[parameters['outputvectorformat']]
        grid = GRID_FORMAT[parameters['outputrasterformat']]
        op = OP[parameters['outputprofile']]
        of = parameters['outputfolder']
        rf = parameters['rootfolder']
        use_scenarios = parameters['usescenarios']
        scenarios = []
        if use_scenarios:
            scenarios = [x.strip() for x in parameters['scenarios'].split(' ') if x.strip()]

        # script path
        script = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'convert_tuflow_model_gis_format',
                              'conv_tf_gis_format', 'convert_tuflow_gis_format.py')
        sys.path.append(os.path.dirname(script))

        args = ['python', '-u', script, '-tcf', str(tcf), '-gis', str(gis), '-grid', str(grid), '-op', str(op)]
        if of:
            args.extend(['-o', str(of)])
        if rf:
            args.extend(['-rf', str(rf)])
        if use_scenarios:
            args.append('-use-scenarios')
            args.extend(scenarios)
        if parameters['gpkg_name'].strip():
            args.extend(['-gpkg-name', parameters['gpkg_name'].strip()])
        if parameters['write_empties']:
            args.append('-write-empties')
            if parameters['empty_directory'].strip():
                args.append(parameters['empty_directory'].strip())
        if parameters['output_crs'] and parameters['output_crs'].isValid():
            args.extend(['-crs', parameters['output_crs'].toWkt()])
        if parameters['tuflow_dir_struct']:
            args.append('-tuflow-dir-struct')
            args.extend(['-tuflow-dir-struct-settings', json.dumps(parameters['tuflow_dir_struct_settings'])])
        if parameters['explode_multipart']:
            args.append('-explode-multipart')

        feedback.pushInfo('args: {0}'.format(args[3:]))

        count = 0
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              creationflags=subprocess.CREATE_NO_WINDOW, bufsize=0, universal_newlines=True) as proc:
            for line in proc.stdout:
                if line.strip():
                    count += 1
                feedback.setCurrentStep(count)
                feedback.pushInfo(line.strip('\n'))

                # Stop the algorithm if cancel button has been clicked
                if feedback.isCanceled():
                    proc.terminate()

        feedback.setProgress(line_count)
        return {}

    def name(self):
        return 'Convert TUFLOW Model GIS Format'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return ''

    def shortHelpString(self):
        return self.tr(
            "<a href=\"https://wiki.tuflow.com/index.php?title=Convert_TUFLOW_Model_GIS_Format\">"
            "Documentation on TUFLOW Wiki</a><p>"
            "<p>"
            "This tool runs a Python script that will convert a given TUFLOW model's vector and raster GIS files "
            "into another, or same, supported TUFLOW format. The script is similar to the package model "
            "functionality that exists in TUFLOW and will try and package files from all "
            "scenarios/events. The difference between the package model functionality and this script, "
            "is that this script will perform additional format conversion steps and update relevant control files."
            "<p>"
            "The tool also gives additional options when converting to GPKG vector and raster formats. The "
            "GPKG format is a database format and allows multiple layers within one file (including a mixture of "
            "vectors and rasters) and the tool gives options on how layers are grouped: "
            "<p>"
            "<p>"
            "Tool Inputs:<p>"
            "<ol>"
            "  <li>TCF: The location of the input TUFLOW model's TCF file to be converted</li>"
            "  <li>Output Vector Format - The output vector format</li>"
            "  <li>Output Raster Format - The output raster format</li>"
            "  <li>Output Profile - For GPKG outputs only - will determine how layers are grouped into databases. "
            "Options:</li>"
            "  <ol>"
            "    <li>SEPARATE will write each layer into its own database. "
            "TUFLOW commands that read multiple geometry types on a single line will all be converted into a single "
            "database.</li>"
            "    <li>GROUP BY CONTROL FILE 1 - will group layers by control file</li>"
            "    <li>GROUP BY CONTROL FILE 2 - similar to GROUP BY CONTROL FILE 1 but will consider "
            "TEF and TRD files as separate control files</li>"
            "    <li>ALL IN ONE - will output every layer into one centralised database</li>"
            "  </ol>"
            "  <li>Output Folder - optional output location for the converted model and files. If none is specified "
            "a folder is created in the same location as the TCF</li>"
            "  <li>Root Folder - only required if the tool can't find the the root folder (traditionally called 'TUFLOW') "
            "where all modelling files sit beneath</li>"
            "  <li>Scenarios: The conversion can be restricted by specifying scenario and event names. Using this "
            "option will stop the conversion of layers that are within an 'IF Scenario/IF Event' logic blocks if the "
            "scenario name is not provided by the user. This option will also clean the control files and remove unused "
            "scenario names. Event names can also be used, however they are only applied to logic blocks in the control "
            "files and are not used to filter event sources provided in the TUFLOW Event File (.tef). To use "
            "this functionality:</li>"
            "  <ol>"
            "    <li>Ensure 'Restrict Conversion by Scenario' is checked on</li>"
            "    <li>List scenario and event names in the text edit. This should be done in the same manner as TUFLOW "
            "batch files e.g. <tt>-s [scenario-name] -e [event-name]</tt>. The order does not matter and numbering "
            "scenarios is not required, although is accepted (e.g. -s1 -s2)</li>"
            "  </ol>"
            "  <li>GPKG Name - sets the output GPKG database name. Only applies to grouped output profiles. If using "
            "a 'grouped by control file' option, then the control file extension will still be added to the name "
            "e.g. [output_name]_TCF.gpkg</li>"
            "  <li>Write Empty Files - creates empty files for the converted model. The location of the empty directory"
            " will be guessed unless a relative path from the root directory (e.g. TUFLOW folder) is provided. The "
            "projection of the empty files will be determined by the first 'Projection == ' command encountered. If "
            "no 'Projection == ' command is present, empty files will not be created.</li>"
            "  <li>Write Empty Files Relative Directory - optional input to be used in conjunction with the Write "
            "Empties checkbox above. The path provided should be a relative path from the root directory (e.g. "
            "commonly this is a folder called 'TUFLOW' - so the relative path may be 'model/gis/empty). If this is not "
            "provided the tool will try and guess where to write empty files.</li>"
            "  <li>Output CRS - Forces output files to be in given projection (no reprojection, or warping is "
            "performed). Useful when converting a model with a combination of SHP and MIF files as these can generate "
            "slightly different projection definitions. Set blank to turn off.</li>"
            "  <li>Force TUFLOW Directory Structure - If this flag is present, the output files will try and be placed "
            "in a standard TUFLOW directory structure (ignoring the input directory structure completely)</li>"
            "  <li>Explode MultiPart Features - If checked, multipart geometry will be exploded into separate features. "
            "</ol>"
        )

    def shortDescription(self):
        return self.tr("Package and convert a TUFLOW model's GIS files into a different format.")

    def createInstance(self):
        return ConvertTuflowModelGisFormat()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
