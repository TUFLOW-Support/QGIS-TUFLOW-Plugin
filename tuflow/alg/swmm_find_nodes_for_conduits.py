import math
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsProcessingFeatureBasedAlgorithm,
                       QgsFeatureSink,
                       QgsFields,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsSpatialIndex,
                       QgsWkbTypes)

from osgeo import ogr, gdal

# import processing
import tempfile

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path
from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper


class FindNodesForConduit(QgsProcessingFeatureBasedAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def __init__(self):
        super().__init__()
        self.input_node_layers = None
        self.node_indices = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return FindNodesForConduit()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMFindNodesForConduits'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Conduits - Assign Node Fields')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagSupportsInPlaceEdits

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
        help_filename = folder / 'help/html/alg_find_nodes_for_conduits.html'
        return help_filename.read_text()

    def supportInPlaceEdit(self, layer):
        return layer.geometryType() == QgsWkbTypes.LineGeometry

    def initParameters(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        self.mapLayerHelperNodeLayers = MapLayerParameterHelper()
        self.mapLayerHelperNodeLayers.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperNodeLayers.setLayerFilter(lambda x: x.name().find('Nodes--') != -1)
        self.mapLayerHelperNodeLayers.refreshLayers()

        # Temp for testing
        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_SWMM_Node_Layers',
                self.tr('SWMM Node Layers (start with Nodes--)'),
                self.mapLayerHelperNodeLayers.getMapLayerNames(),
                allowMultiple=True,
                optional=True,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterMultipleLayers(
        #         'INPUT_SWMM_Node_Layers',
        #         self.tr('SWMM Node Layers'),
        #         QgsProcessing.TypeVectorPoint,
        #     )
        # )

    def outputName(self):
        return self.tr('Conduits')

    def outputType(self):
        return QgsProcessing.TypeVectorPolyline

    def outputWkbType(self, inputWkbType):
        return inputWkbType

    def prepareAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        lays_node_layers_pos = self.parameterAsEnums(parameters,
                                                     'INPUT_SWMM_Node_Layers',
                                                     context)
        self.input_node_layers = self.mapLayerHelperNodeLayers.getLayersFromIndices(lays_node_layers_pos)

        # self.input_node_layers = self.parameterAsLayerList(parameters,
        #                                                    'INPUT_SWMM_Node_Layers',
        #                                                    context)

        feedback.pushInfo('\n'.join([str(x) for x in self.input_node_layers]))

        self.node_indices = [QgsSpatialIndex(x.getFeatures()) for x in self.input_node_layers]

        return True

    def processFeature(self, feature, context, feedback):
        tolerance = 0.001

        if not feature.hasGeometry() or feature.geometry().type() != QgsWkbTypes.LineGeometry:
            self.feedback.reportError('Feature encountered with improper geometry. Only Polylines are supported.',
                                      fatalError=True)
            return []

        # Do upstream nodes
        self.handle_conduits_side_single_feature(feature,
                                                 self.input_node_layers,
                                                 tolerance,
                                                 0,
                                                 'From Node',
                                                 self.node_indices)

        # Do downstream nodes
        self.handle_conduits_side_single_feature(feature,
                                                 self.input_node_layers,
                                                 tolerance,
                                                 -1,
                                                 'To Node',
                                                 self.node_indices)

        return [feature]

    def distance(self, x1, y1, x2, y2):
        return math.sqrt(pow(x1 - x2, 2) + pow((y1 - y2), 2))

    def handle_conduits_side_single_feature(self,
                                            feature,
                                            layers_nodes,
                                            tolerance,
                                            conduit_node_index,
                                            node_attribute,
                                            node_indices):
        # Get the upstream node of the polyline
        upstream_node = feature.geometry().asPolyline()[conduit_node_index]
        field_index = feature.fields().indexOf(node_attribute)

        # Look for a node and stop at the first one
        close_nodes = []  # (node, distance)
        for layer_nodes, node_index in zip(layers_nodes, node_indices):
            # Use the spatial index to find nodes within the tolerance distance of the upstream node
            nearby_nodes = node_index.nearestNeighbor(QgsPointXY(upstream_node), 1, tolerance)

            if nearby_nodes:
                node_feature = layer_nodes.getFeature(nearby_nodes[0])
                close_nodes.append((node_feature,
                                    self.distance(node_feature.geometry().asQPointF().x(),
                                                  node_feature.geometry().asQPointF().y(),
                                                  upstream_node.x(),
                                                  upstream_node.y())))

        close_nodes.sort(key=lambda x: x[1])

        # Close nodes will be in order from closest to furthest
        if not close_nodes or close_nodes[0][1] > tolerance:
            conduit_start_or_end = 'start' if conduit_node_index == 0 else 'end'
            self.feedback.pushWarning(
                f'No node found within tolerance for {feature["Name"]} at {conduit_start_or_end}.')
            if feature[node_attribute] != '':
                feature[node_attribute] = ''
        else:
            close_node = close_nodes[0][0]
            if feature[node_attribute] != close_node['Name']:
                change_text = f'Changing {feature["Name"]} {node_attribute} to {close_node["Name"]}'
                self.feedback.pushInfo(change_text)
                feature[node_attribute] = close_node['Name']
