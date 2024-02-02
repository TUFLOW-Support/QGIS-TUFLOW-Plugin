import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis._core import QgsProcessingParameterEnum
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

import tempfile

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.tuflow_swmm.create_endpoint_connections import create_endpoint_connections


class CreateEndpointConnections(QgsProcessingAlgorithm):
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
        return CreateEndpointConnections()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMCreateEndpointConnections'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('BC - Create channel endpoint 1D/2D connections')

    def flags(self):
        return super().flags()

    def supportInPlaceEdit(self, layer):
        return False

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
        help_filename = folder / 'help/html/alg_create_endpoint_connections.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # print(config)
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                'INPUT',
                self.tr('Input Conduits Layer'),
                types=[QgsProcessing.TypeVector]
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_location_option',
                self.tr('Create connections at '),
                [
                    'Both ends',
                    'Upstream end',
                    'Downstream end',
                ],
                allowMultiple=False,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_offset_distance',
                self.tr('Offset distance'),
                10.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_bc_length',
                self.tr('Length of BC lines'),
                15.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                'Input_set_z_flag',
                self.tr('Set 2D cell elevation to 1D culvert invert at 1D/2D connection cells if needed')
            )
        )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                self.tr('Output Layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        input_source = self.parameterAsSource(parameters,
                                              'INPUT',
                                              context)

        location_option = int(self.parameterAsString(
            parameters,
            'Input_location_option',
            context,
        ))
        create_upstream = location_option != 2
        create_downstream = location_option != 1

        if create_upstream:
            feedback.pushInfo('Creating upstream segments.')

        if create_downstream:
            feedback.pushInfo('Creating downstream segments.')

        offset_dist = self.parameterAsDouble(parameters,
                                             'Input_offset_distance',
                                             context)

        width = self.parameterAsDouble(parameters,
                                       'Input_bc_length',
                                       context)

        set_z_flag = self.parameterAsBool(parameters,
                                          'Input_set_z_flag',
                                          context)

        output_sink, output_layer = self.parameterAsSink(
            parameters,
            'OUTPUT',
            context,
            QgsFields(),
            input_source.wkbType(),
            input_source.sourceCrs(),
        )
        if isinstance(output_layer, str):
            output_layer = QgsProcessingUtils.mapLayerFromString(
                output_layer,
                context)

        if feedback.isCanceled():
            return {}

        create_endpoint_connections(input_source,
                                    offset_dist,
                                    width,
                                    set_z_flag,
                                    output_layer,
                                    create_upstream,
                                    create_downstream,
                                    self.feedback,
                                    )

        result_dict = {
            'OUTPUT': output_layer,
        }

        # Return the results
        return result_dict
