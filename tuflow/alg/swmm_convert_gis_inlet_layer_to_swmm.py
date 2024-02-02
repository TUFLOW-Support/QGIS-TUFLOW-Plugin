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
                       QgsProcessingParameterField,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterString,
                       QgsProcessingUtils,
                       QgsSpatialIndex)

has_fiona = False
try:
    import fiona
    has_fiona = True
except ImportError:
    pass # defaulted to False
from osgeo import ogr, gdal

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

# import processing
import tempfile
# from .swmmutil import copy_features
from tuflow.tuflow_swmm.xpswmm_node2d_convert import xpswmm_2d_capture_to_swmm


class ConvertGISInletLayer(QgsProcessingAlgorithm):
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
        return ConvertGISInletLayer()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TUFLOWConvertGISInletLayerToSWMM'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Convert - XPSWMM GIS inlet layers to SWMM')

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
        help_filename = folder / 'help/html/alg_convert_xpswmm_gis_inlet_layer.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterMapLayer(
                'INPUT',
                self.tr('GIS layer with inlet information'),
                types=[QgsProcessing.TypeVectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_inlet_name',
                self.tr('Inlet name field'),
                type=QgsProcessingParameterField.DataType.String,
                optional=False,
                parentLayerParameterName='INPUT',
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_inlet_elevation',
                self.tr('Inlet elevation field'),
                type=QgsProcessingParameterField.DataType.Numeric,
                optional=False,
                parentLayerParameterName='INPUT',
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_inlet_2d_capture_flag',
                self.tr('Inlet 2d capture flag (1=has 2d connection) field'),
                type=QgsProcessingParameterField.DataType.Numeric,
                optional=False,
                parentLayerParameterName='INPUT',
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_inlet_q_coeff',
                self.tr('Inlet discharge equation coefficient field'),
                type=QgsProcessingParameterField.DataType.Numeric,
                optional=False,
                parentLayerParameterName='INPUT',
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                'INPUT_inlet_q_exponent',
                self.tr('Inlet discharge exponent field'),
                type=QgsProcessingParameterField.DataType.Numeric,
                optional=False,
                parentLayerParameterName='INPUT',
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_inlet_connection_width',
                self.tr('Inlet connection width'),
                QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=0.001,
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                'INPUT_crs',
                self.tr('CRS'),
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_inp_file',
                self.tr('SWMM inp file (for inlet definition and curves)'),
                fileFilter='inp',
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                'OUTPUT_iu_file',
                self.tr('Geo-Package file for inlet usage (for inlet placement)'),
                fileFilter='gpkg',
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        layer_gis_iu = self.parameterAsLayer(parameters,
                                             'INPUT',
                                             context)
        layer_gis_iu_atts = layer_gis_iu.source().split('|')
        layer_gis_iu_filename = layer_gis_iu_atts[0]
        layer_gis_iu_layername = None
        if len(layer_gis_iu_atts) > 1:
            layergis_iu_layername = [x[1] for x in layer_gis_iu_atts[1:] if x.find('layername') != -1]

        field_node_name = self.parameterAsString(parameters,
                                                 'INPUT_inlet_name',
                                                 context)

        field_inlet_elevation = self.parameterAsString(parameters,
                                                       'INPUT_inlet_elevation',
                                                       context)

        field_inlet_2d_capture_flag = self.parameterAsString(parameters,
                                                             'INPUT_inlet_2d_capture_flag',
                                                             context)

        field_inlet_q_coeff = self.parameterAsString(parameters,
                                                     'INPUT_inlet_q_coeff',
                                                     context)

        field_inlet_q_exponent = self.parameterAsString(parameters,
                                                        'INPUT_inlet_q_exponent',
                                                        context)

        connection_width = self.parameterAsDouble(parameters,
                                                  'INPUT_inlet_connection_width',
                                                  context)

        crs = self.parameterAsCrs(parameters,
                                  'INPUT_crs',
                                  context)
        crs_text = crs.toWkt()

        inp_file = Path(self.parameterAsFile(parameters,
                                             'OUTPUT_inp_file',
                                             context))

        gpkg_file = Path(self.parameterAsFile(parameters,
                                              'OUTPUT_iu_file',
                                              context))

        xpswmm_2d_capture_to_swmm(
            layer_gis_iu_filename,
            field_node_name,
            field_inlet_elevation,
            field_inlet_2d_capture_flag,
            field_inlet_q_coeff,
            field_inlet_q_exponent,
            connection_width,
            crs_text,
            inp_file,
            gpkg_file,
            feedback
        )

        result_dict = {
            'OUTPUT': f'Files: {inp_file} and {gpkg_file}',
        }

        # Return the results
        return result_dict
