import json

from qgis.PyQt.QtCore import QCoreApplication
from qgis._core import QgsProcessingParameterBoolean, QgsProcessingParameterString, QgsProcessingModelGroupBox, \
    QgsProcessingParameterCrs, QgsProcessingParameterFeatureSource
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingParameterDefinition
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterEnum
from qgis import processing
import subprocess
import sys
import time
import re
import os
from pathlib import Path

from ..gui.processing.processsing_param_conv_tuf_model_format_dir_settings import \
    ProcessingParameterConvTufModelDirSettings

from tuflow.tuflow_swmm.xpswmm_xpx_convert import convert_xpswmm

GIS_FORMAT = {0: 'GPKG', 1: 'SHP', 2: 'MIF'}
GRID_FORMAT = {0: 'TIF', 1: 'GPKG', 2: 'FLT', 3: 'ASC'}
OP = {0: 'SEPARATE', 1: 'CF1', 2: 'CF2', 3: 'TCF'}

solution_scheme_options = ['HPC', 'CLA']
hardware_options = ['GPU', 'CPU']


class SwmmXpswmmConvert(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile(
            'xpx_file',
            'XPSWMM Exported XPX File',
            behavior=QgsProcessingParameterFile.File,
            fileFilter='XPX (*.xpx *.XPX)',
            defaultValue=None)
        )
        self.addParameter(QgsProcessingParameterFile('tcf',
                                                     'TUFLOW TCF Filename',
                                                     behavior=QgsProcessingParameterFile.File,
                                                     fileFilter='TCF (*.tcf *.TCF)',
                                                     defaultValue=None))
        self.addParameter(QgsProcessingParameterString(
            'swmm_prefix',
            'SWMM File Prefix',
            defaultValue=None,
        )
        )
        self.addParameter(QgsProcessingParameterEnum('solution_scheme',
                                                     'Output Solution Scheme',
                                                     options=solution_scheme_options,
                                                     allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('hardware',
                                                     'Output Hardware Specification',
                                                     options=hardware_options,
                                                     allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('outputvectorformat',
                                                     'Output Vector Format',
                                                     options=['GPKG',
                                                              'SHP',
                                                              'MIF'],
                                                     allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('outputrasterformat',
                                                     'Output Raster Format',
                                                     options=['GTIFF',
                                                              'GPKG',
                                                              'FLT',
                                                              'ASC'],
                                                     allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterEnum('outputprofile',
                                                     'Output Profile',
                                                     options=['SEPARATE',
                                                              'GROUP BY CONTROL FILE 1',
                                                              'GROUP BY CONTROL FILE 2',
                                                              'ALL IN ONE'],
                                                     allowMultiple=False,
                                                     defaultValue=[0]))
        self.addParameter(QgsProcessingParameterString('default_event',
                                                       'Event name if no global storms',
                                                       defaultValue='event1',
                                                       optional=False))
        self.addParameter(QgsProcessingParameterFile('outputfolder',
                                                     'Output Folder',
                                                     optional=False,
                                                     behavior=QgsProcessingParameterFile.Folder,
                                                     fileFilter='All files (*.*)',
                                                     defaultValue=None))
        param = QgsProcessingParameterCrs('output_crs',
                                          'Output CRS',
                                          optional=False)
        self.addParameter(param)

    def processAlgorithm(self, parameters, context, model_feedback):
        # params
        tcf = parameters['tcf']
        gis = parameters['outputvectorformat']
        grid = parameters['outputrasterformat']
        op = parameters['outputprofile']
        of = parameters['outputfolder']
        crs = parameters['output_crs']
        default_event = parameters['default_event']

        struct_json = (Path(
            __file__).parent.parent / 'convert_tuflow_model_gis_format' / 'conv_tf_gis_format' / 'data' /
                       'dir_relationships.json')
        with struct_json.open() as fo:
            default_struct = json.load(fo)

        params_gis_format = {
            'tcf': tcf,
            'outputvectorformat': gis,
            'outputrasterformat': grid,
            'outputprofile': op,
            'outputfolder': of,
            'output_crs': crs,
            'write_empties': True,
            'tuflow_dir_struct': True,
            'usescenarios': False,
            'rootfolder': None,
            'gpkg_name': '',
            'empty_directory': '',
            'tuflow_dir_struct_settings': default_struct,
        }

        # Convert the TUFLOW model
        processing.run('TUFLOW:Convert TUFLOW Model GIS Format',
                       params_gis_format,
                       feedback=model_feedback)

        xpx_filename = parameters['xpx_file']
        swmm_prefix = parameters['swmm_prefix']
        solution_scheme = solution_scheme_options[parameters['solution_scheme']]
        hardware = hardware_options[parameters['hardware']]

        created_tcf_filename = Path(of) / f'runs\\{Path(tcf).name}'

        convert_xpswmm(
            xpx_filename,
            created_tcf_filename,
            swmm_prefix,
            solution_scheme,
            hardware,
            default_event,
            crs.toWkt(),
            model_feedback,
        )

        return {}

    def name(self):
        return 'Convert - XPSWMM Model from XPX (Beta)'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr('SWMM')

    def groupId(self):
        return 'TuflowSWMM_Tools'

    def shortHelpString(self):
        """
        Returns a localised short help string for the algorithm.
        """
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help/html/alg_swmm_xpswmm_convert.html'
        return help_filename.read_text()

    def shortDescription(self):
        return self.tr("Convert 1D (xpx) and 2D (tcf) portions of XPSWMM model to TUFLOW-SWMM.")

    def createInstance(self):
        return SwmmXpswmmConvert()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)