import os
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis._core import QgsProcessingParameterEnum, QgsProcessingParameterVectorLayer
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsField,
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

has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper
from tuflow.geopandas.gpd_to_layer import fill_layer_from_gdf
from tuflow.tuflow_swmm.convert_nonoutfall_sx_to_hx import convert_nonoutfall_sx_to_hx_gdfs
from tuflow.toc.toc import tuflowqgis_find_layer


class BcConvertNonOutfallSxToHx(QgsProcessingAlgorithm):
    """
    This processing tool converts SX connections to HX connections if connected to a non-outfall node
    """

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return BcConvertNonOutfallSxToHx()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMBcNonOutfallSxToHx'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('BC - Convert Non-Outfall SX Connections to HX')

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagNoThreading

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
        help_filename = folder / 'help/html/alg_swmm_bc_non_outfall_sx_to_hx.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'bc_in',
                'Boundary condition layer (2d_bc)',
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None
            )
        )

        self.mapLayerHelperNodeLayers = MapLayerParameterHelper()
        self.mapLayerHelperNodeLayers.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperNodeLayers.refreshLayers()

        self.mapLayerNodeLayersParam = QgsProcessingParameterEnum(
            'INPUT_node_layers',
            self.tr('SWMM Node Layers (select non-outfall layers)'),
            self.mapLayerHelperNodeLayers.getMapLayerNames(),
            allowMultiple=True,
            optional=False,
        )
        self.addParameter(self.mapLayerNodeLayersParam)
        self.mapLayerNodeLayersParam.setOptions(self.mapLayerHelperNodeLayers.getMapLayerNames())

        self.mapLayerHelperIULayers = MapLayerParameterHelper()
        self.mapLayerHelperIULayers.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperIULayers.refreshLayers()

        self.mapLayerIULayersParam = QgsProcessingParameterEnum(
            'INPUT_iu_layers',
            self.tr('SWMM Input Usage Layers'),
            self.mapLayerHelperIULayers.getMapLayerNames(),
            allowMultiple=True,
            optional=True,
        )
        self.addParameter(self.mapLayerIULayersParam)
        self.mapLayerIULayersParam.setOptions(self.mapLayerHelperIULayers.getMapLayerNames())

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                self.tr('Output BC Layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        if not has_gpd:
            message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                       'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
            feedback.reportError(message, fatalError=True)

        self.feedback = feedback

        bc_layer = self.parameterAsLayer(parameters, 'bc_in', context)

        node_layer_pos = self.parameterAsEnums(parameters,
                                               'INPUT_node_layers',
                                               context)
        node_layer_names = [self.mapLayerNodeLayersParam.options()[x] for x in node_layer_pos]
        node_layers = self.mapLayerHelperNodeLayers.getLayersFromNames(node_layer_names)

        self.feedback.pushInfo(f'Node layer names:')
        for node_layer in node_layer_names:
            self.feedback.pushInfo(f'\t{node_layer}')

        iu_layer_pos = self.parameterAsEnums(parameters,
                                               'INPUT_iu_layers',
                                               context)
        iu_layer_names = [self.mapLayerIULayersParam.options()[x] for x in iu_layer_pos]
        iu_layers = self.mapLayerHelperIULayers.getLayersFromNames(iu_layer_names)

        self.feedback.pushInfo(f'Inlet usage layer names:')
        for iu_layer in iu_layer_names:
            self.feedback.pushInfo(f'\t{iu_layer}')

        output_sink, output_layer = self.parameterAsSink(
            parameters,
            'OUTPUT',
            context,
            QgsFields(),
            bc_layer.wkbType(),
            bc_layer.sourceCrs(),
        )
        if isinstance(output_layer, str):
            output_layer = QgsProcessingUtils.mapLayerFromString(
                output_layer,
                context)

        if feedback.isCanceled():
            return {}

        layer_features = list(bc_layer.getFeatures())
        gdf_in = gpd.GeoDataFrame.from_features(layer_features)

        gdfs_swmm = [gpd.GeoDataFrame.from_features(x.getFeatures()) for x in node_layers]
        gdf_swmm = gpd.GeoDataFrame(pd.concat([x[['Name', 'geometry']] for x in gdfs_swmm], axis=0))

        gdf_iu = None
        if len(iu_layers) > 0:
            gdfs_iu = [gpd.GeoDataFrame.from_features(x.getFeatures()) for x in iu_layers]
            gdf_iu = gpd.GeoDataFrame(pd.concat([x[['Inlet', 'geometry']] for x in gdfs_iu], axis=0))

        gdf_out = convert_nonoutfall_sx_to_hx_gdfs(
            gdf_swmm,
            gdf_in,
            gdf_iu,
            feedback,
        )

        fill_layer_from_gdf(output_layer, gdf_out)

        result_dict = {
            'OUTPUT': output_layer,
        }

        # Return the results
        return result_dict
