from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputFile,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterCrs,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterString,
                       QgsProcessingUtils,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from ..gui.logging import Logging

# import processing
import tempfile
# from .swmmutil import copy_features
from tuflow.tuflow_swmm import estry_to_swmm_gis_layers as estry_layers_to_swmm
from tuflow.tuflow_swmm import swmm_defaults
from tuflow.tuflow_swmm import create_swmm_section_gpkg as swmm_gpkg


def convert_source_to_filename(source):
    # For Geo-Packages we want to keep the layernames provided. Other formats will not use it
    source_atts = source.split('|')
    filename = source_atts[0]
    layername = [x.split('=')[1] for x in source_atts[1:] if x.find('layername') != -1]
    if len(layername) == 0:
        layername = None
    else:
        layername = layername[0]
    if layername and filename.find('.gpkg') != -1:
        # find the sourceatt for the layername
        filename = filename + '/' + layername

    return filename


class ConvertESTRYLayers(QgsProcessingAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ConvertESTRYLayers()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TUFLOWConvertESTRYLayersToSWMM'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Convert - ESTRY Layers to SWMM')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagNoThreading

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('SWMM')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs
        to.
        """
        return 'TuflowSWMM_Tools'

    def shortHelpString(self):
        """
        Returns a localised short help string for the algorithm.
        """
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help/html/alg_estry_to_swmm_layers.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                'INPUT_nwk_layers',
                self.tr('<br><b>Network Options</b><br><br>ESTRY Network Layers'),
                layerType=QgsProcessing.TypeVectorAnyGeometry,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                'INPUT_nd_layers',
                self.tr('ESTRY Node Layers'),
                layerType=QgsProcessing.TypeVectorPoint,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                'INPUT_pit_layers',
                self.tr('ESTRY Pit Layers'),
                layerType=QgsProcessing.TypeVectorPoint,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                'INPUT_xs_layers',
                self.tr('ESTRY Table Link Layers'),
                layerType=QgsProcessing.TypeVectorLine,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT_pit_inlet_dbase',
                self.tr('ESTRY Pit Inlet Database'),
                extension='csv',
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_reference_cell_size',
                self.tr('Reference cell size for inlet connections'),
                QgsProcessingParameterNumber.Double,
                defaultValue=25.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_snap_tolerance',
                self.tr('Network snap tolerance'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.001,
                minValue=0.000001,
            )
        )

        param = QgsProcessingParameterCrs('OUTPUT_crs', 'Output CRS')
        self.addParameter(param)

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_create_tables',
                self.tr('<br><hr><b>Extra Tables</b><br><br>Create options, and report tables'),
                ['Yes', 'No'],
                defaultValue='Yes',
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterBoolean(
        #         'INPUT_create_tables',
        #        '<br><hr><b>Extra Tables</b><br><br>Create options, and report tables',
        #         defaultValue=True,
        #     )
        # )

        self.addParameter(
            QgsProcessingParameterString(
                'INPUT_report_step',
                self.tr('Options table report step (hh:mm:ss)'),
                defaultValue='00:10:00',
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_min_surface_area',
                self.tr('Options table minimum surface area'),
                QgsProcessingParameterNumber.Double,
                defaultValue=25.0,
                minValue=0.1,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_swmm_output_filename',
                self.tr('<br><hr><b>Output Options</b><br><br>SWMM output filename'),
                fileFilter='*.inp',
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_ext_inlet_usage_filename',
                self.tr('SWMM inlet usage Geo-Package filename'),
                fileFilter='*.gpkg',
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterFile(
        #         'INPUT_ta_check_file',
        #         self.tr('ESTRY ta check file'),
        #         extension='csv',
        #     )
        # )
        # self.addParameter(
        #     QgsProcessingParameterFileDestination(
        #         'INPUT_swmm_output_filename',
        #         self.tr('SWMM output filename'),
        #         fileFilter='*.inp',
        #     )
        # )
        #
        # self.addParameter(
        #     QgsProcessingParameterFileDestination(
        #         'INPUT_inlet_usage_filename',
        #         self.tr('Inlet usage filename'),
        #         fileFilter='*.gpkg',
        #     )
        # )
        #
        # self.addParameter(
        #     QgsProcessingParameterNumber(
        #         'INPUT_default_ponding_area',
        #         self.tr('SWMM default ponding area'),
        #         QgsProcessingParameterNumber.Double,
        #         defaultValue=25.0,
        #         minValue=0.0,
        #     )
        # )
        #
        # self.addParameter(
        #     QgsProcessingParameterNumber(
        #         'INPUT_reference_cell_size',
        #         self.tr('Reference cell size to set inlet Conn_width'),
        #         QgsProcessingParameterNumber.Double,
        #         defaultValue=5.0,
        #         minValue=0.0,
        #     )
        # )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        # self.addOutput(
        #     QgsProcessingOutputFile(
        #         'OUTPUT',
        #         self.tr('SWMM output filename')
        #     )
        # )

    def mapLayersToListOfFiles(self, layer_type, map_layers):
        self.feedback.pushInfo(f'{layer_type} ({len(map_layers)})')
        # file_list = [x.source().replace('|layername=', '/') for x in map_layers]
        file_list = [convert_source_to_filename(x.source()) for x in map_layers]
        for file in file_list:
            self.feedback.pushInfo(f'  {file}')
        self.feedback.pushInfo('\n')
        return file_list

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        report_step = '0:05:00'
        min_surfarea = '3'
        street_name = 'DummyStreet'
        street_slope_pct = 4.0
        inlet_placement = 'OnSag'
        crs = ''

        feedback.pushInfo('\nDefaults:')
        feedback.pushInfo(f'\tReport step: {report_step}')
        feedback.pushInfo(f'\tMinimum surface area: {min_surfarea}')
        feedback.pushInfo(f'\tInlet placement: {inlet_placement}')
        feedback.pushInfo(f'Street info does not impact results for OnSag inlet placement')
        feedback.pushInfo(f'\tStreet name: {street_name}')
        feedback.pushInfo(f'\tStreet Slope Percent: {street_slope_pct} %')
        feedback.pushInfo('\n\n')

        nwk_layers = self.parameterAsLayerList(parameters,
                                               'INPUT_nwk_layers',
                                               context)
        nwk_files = self.mapLayersToListOfFiles('ESTRY Network Layers', nwk_layers)

        nd_layers = self.parameterAsLayerList(parameters,
                                              'INPUT_nd_layers',
                                              context)
        nd_files = self.mapLayersToListOfFiles('ESTRY Node Layers', nd_layers)

        pit_layers = self.parameterAsLayerList(parameters,
                                               'INPUT_pit_layers',
                                               context)
        pit_files = self.mapLayersToListOfFiles('ESTRY Pit Layers', pit_layers)

        xs_layers = self.parameterAsLayerList(parameters,
                                              'INPUT_xs_layers',
                                              context)
        xs_files = self.mapLayersToListOfFiles('ESTRY Table Link Layers', xs_layers)

        pit_inlet_dbase = self.parameterAsFile(parameters,
                                               'INPUT_pit_inlet_dbase',
                                               context)
        if pit_inlet_dbase == '':
            pit_inlet_dbase = None
            feedback.pushInfo(f'No Pit Inlet Database')
        else:
            feedback.pushInfo(f'Pit Inlet Database: {pit_inlet_dbase}')

        reference_cell_size = self.parameterAsDouble(parameters,
                                                     'INPUT_reference_cell_size',
                                                     context)
        feedback.pushInfo(f'Reference cell size: {reference_cell_size}')

        snap_tolerance = self.parameterAsDouble(parameters,
                                                'INPUT_snap_tolerance',
                                                context)
        feedback.pushInfo(f'Snap tolerance: {snap_tolerance}')

        output_crs = self.parameterAsCrs(parameters,
                                         'OUTPUT_crs',
                                         context)
        feedback.pushInfo(f'Output CRS: {output_crs}')

        create_tables = self.parameterAsInt(parameters,
                                            'INPUT_create_tables',
                                            context) == 0
        if create_tables:
            feedback.pushInfo(f'Creating options and report tables.')
        else:
            feedback.pushInfo(f'Not creating options and report tables.')

        report_step = self.parameterAsString(parameters,
                                             'INPUT_report_step',
                                             context)

        min_surface_area = self.parameterAsString(parameters,
                                                  'Input_min_surface_area',
                                                  context)

        if create_tables:
            feedback.pushInfo(f'Creating output and reporting tables')
            feedback.pushInfo(f'Report step: {report_step}')
            feedback.pushInfo(f'Min surface area: {min_surfarea}\n')

        output_swmm_filename = self.parameterAsString(parameters,
                                                      'OUTPUT_swmm_output_filename',
                                                      context)
        feedback.pushInfo(f'Output filename: {output_swmm_filename}')

        output_ext_inlet_usage_filename = self.parameterAsString(parameters,
                                                                 'OUTPUT_ext_inlet_usage_filename',
                                                                 context)
        feedback.pushInfo(f'Output inlet usage filename: {output_ext_inlet_usage_filename}')

        # pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)

        feedback.pushInfo(f'{output_crs.toWkt()}')

        estry_layers_to_swmm.convert_layers(
            nwk_files, nd_files, pit_files, xs_files,
            pit_inlet_dbase,
            street_name, street_slope_pct, reference_cell_size,
            create_tables, report_step, min_surface_area,
            snap_tolerance,
            Path(output_swmm_filename).with_suffix('.gpkg'), output_ext_inlet_usage_filename,
            output_crs.toWkt(),
            feedback,
            Logging,
        )

        result_dict = {
            'OUTPUT': f'{output_swmm_filename}\n{output_ext_inlet_usage_filename}',
        }

        # Return the results
        return result_dict
