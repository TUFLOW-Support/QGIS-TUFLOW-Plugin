import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingFeatureBasedAlgorithm,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterEnum,
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

from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper
from tuflow.tuflow_swmm.junctions_downstream_to_outfalls import downstream_junctions_to_outfalls_from_qgis


class DownstreamJunctionsToOutfalls(QgsProcessingAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def __init__(self):
        super().__init__()
        self.mapLayerHelperLinks = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return DownstreamJunctionsToOutfalls()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMDownstreamJunctionsToOutfalls'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Junctions - Downstream Junctions to Outfalls')

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
        help_filename = folder / 'help/html/alg_downstream_junctions_to_outfalls.html'
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
                self.tr('Input junctions'),
                types=[QgsProcessing.TypeVectorPoint],
            )
        )

        self.mapLayerHelperLinks = MapLayerParameterHelper()
        self.mapLayerHelperLinks.setMapLayerType(QgsProcessing.TypeVectorLine)
        self.mapLayerHelperLinks.setLayerFilter(lambda x: x.name().find('Links--') != -1)
        self.mapLayerHelperLinks.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_conduits',
                self.tr('Input conduits (starts with Links--)'),
                self.mapLayerHelperLinks.getMapLayerNames(),
                allowMultiple=True,
                optional=False,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterMultipleLayers(
        #         'INPUT_conduits',
        #         self.tr('Input conduits'),
        #         layerType=QgsProcessing.TypeVectorAnyGeometry,
        #     )
        # )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_junctions',
                self.tr('Modified junctions layer')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_outfalls',
                self.tr('New outfalls layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        junction_source = self.parameterAsSource(parameters,
                                                 'INPUT',
                                                 context)

        conduit_layers_pos = self.parameterAsEnums(parameters,
                                                   'Input_conduits',
                                                   context)
        conduit_layers = self.mapLayerHelperLinks.getLayersFromIndices(conduit_layers_pos)

        # counduit_source = self.parameterAsLayerList(parameters,
        #                                            'INPUT_conduits',
        #                                            context)

        output_sink_junctions, output_layer_junctions = self.parameterAsSink(
            parameters,
            'OUTPUT_junctions',
            context,
            QgsFields(),
            junction_source.wkbType(),
            junction_source.sourceCrs(),
        )
        if isinstance(output_layer_junctions, str):
            output_layer_junctions = QgsProcessingUtils.mapLayerFromString(
                output_layer_junctions,
                context)
        else:
            feedback.reportError('Junction output layer is inavlid.', fatalError=True)

        output_sink_outfalls, output_layer_outfalls = self.parameterAsSink(
            parameters,
            'OUTPUT_outfalls',
            context,
            QgsFields(),
            junction_source.wkbType(),
            junction_source.sourceCrs(),
        )
        if isinstance(output_layer_outfalls, str):
            output_layer_outfalls = QgsProcessingUtils.mapLayerFromString(
                output_layer_outfalls,
                context)
        else:
            feedback.reportError('Junction output layer is inavlid.', fatalError=True)

        if feedback.isCanceled():
            return {}

        downstream_junctions_to_outfalls_from_qgis(
            junction_source,
            conduit_layers,
            output_layer_junctions,
            output_layer_outfalls,
            feedback,
        )

        result_dict = {
            'OUTPUT_junctions': output_layer_junctions,
            'OUTPUT_outfalls': output_layer_outfalls,
        }

        # Return the results
        return result_dict
