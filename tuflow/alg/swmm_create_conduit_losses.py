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
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsWkbTypes,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

import tempfile

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.tuflow_swmm.create_conduit_losses import get_conduit_loss_info
from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper

class CreateConduitLosses(QgsProcessingFeatureBasedAlgorithm):
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
        return CreateConduitLosses()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMCreateConduitLosses'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Conduits - Assign Losses')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagSupportsInPlaceEdits

    def supportInPlaceEdit(self, layer):
        return layer.geometryType() == QgsWkbTypes.LineGeometry

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
        help_filename = folder / 'help/html/alg_create_conduit_losses.html'
        return help_filename.read_text()

    def outputName(self):
        return self.tr('Output conduits')

    def outputType(self):
        return QgsProcessing.TypeVectorPolyline

    def outputWkbType(self, inputWkbType):
        return inputWkbType

    def initParameters(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # print(config)
        # 'INPUT' is the recommended name for the main input
        # parameter.
        # self.addParameter(
        #    QgsProcessingParameterFeatureSource(
        #        'INPUT',
        #        self.tr('Input conduit features'),
        #        types=[QgsProcessing.TypeVector],
        #    )
        # )

        self.mapLayerHelperInletUsage = MapLayerParameterHelper()
        self.mapLayerHelperInletUsage.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperInletUsage.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_inlets',
                self.tr('Input Inlet Usage Layers'),
                self.mapLayerHelperInletUsage.getMapLayerNames(),
                allowMultiple=True,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_up_entrance_loss',
                self.tr('<br><hr><b>Culvert opening</b><br><br>Entrance loss'),
                QgsProcessingParameterNumber.Double,
                0.5,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_down_exit_loss',
                self.tr('<br><hr><b>Culvert or pipe network outlet</b><br><br>Exit loss'),
                QgsProcessingParameterNumber.Double,
                1.0,
            )
        )


        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_other_entrance_loss',
                self.tr('<br><hr><b>Pipe network (manholes and pit inlets)</b><br><br>Entrance loss'),
                QgsProcessingParameterNumber.Double,
                0.2,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_other_exit_loss',
                self.tr('Exit loss'),
                QgsProcessingParameterNumber.Double,
                0.4,
            )
        )


    def prepareAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        conduit_source = self.parameterAsSource(parameters,
                                                'INPUT',
                                                context)

        lays_inlet_usage_pos = self.parameterAsEnums(parameters,
                                                     'INPUT_inlets',
                                                     context)
        self.inlet_layers = self.mapLayerHelperInletUsage.getLayersFromIndices(lays_inlet_usage_pos)

        #self.inlet_layers = self.parameterAsLayerList(parameters,
        #                                              'INPUT_inlets',
        #                                              context)

        self.up_entrance_loss = self.parameterAsDouble(parameters,
                                                       'Input_up_entrance_loss',
                                                       context)

        self.other_entrance_loss = self.parameterAsDouble(parameters,
                                                          'Input_other_entrance_loss',
                                                          context)

        self.down_exit_loss = self.parameterAsDouble(parameters,
                                                     'Input_down_exit_loss',
                                                     context)

        self.other_exit_loss = self.parameterAsDouble(parameters,
                                                      'Input_other_exit_loss',
                                                      context)

        # output_sink, output_layer = self.parameterAsSink(
        #    parameters,
        #    'OUTPUT',
        #    context,
        #    QgsFields(),
        #    conduit_source.wkbType(),
        #    conduit_source.sourceCrs(),
        # )
        # if isinstance(output_layer, str):
        #    output_layer = QgsProcessingUtils.mapLayerFromString(
        #        output_layer,
        #        context)

        if feedback.isCanceled():
            return False

        try:
            self.df_losses = get_conduit_loss_info(
                conduit_source,
                self.inlet_layers,
                self.feedback,
            )
        except:
            # If we get here, something went wrong
            return False

        self.feedback.pushInfo('Finished prepareAlgorithm')
        return True

    def processFeature(self, feature, context, feedback):
        try:
            self.feedback.pushInfo(f'Processing feature: {feature["Name"]}')
            has_upstream = self.df_losses.loc[self.df_losses['Name'] == feature['Name'], 'HasUpstream'].iloc[0]
            has_downstream = self.df_losses.loc[self.df_losses['Name'] == feature['Name'], 'HasDownstream'].iloc[0]

            has_inlet_us = str(self.df_losses.loc[self.df_losses['Name'] == feature['Name'], 'Inlet_us'].iloc[
                                0]).lower() != 'nan'

            has_inlet_ds = str(self.df_losses.loc[self.df_losses['Name'] == feature['Name'], 'Inlet_ds'].iloc[
                                0]).lower() != 'nan'

            is_openchannel = self.df_losses.loc[self.df_losses['Name'] == feature['Name'], 'IsOpenChannel'].iloc[0]

            # No losses for open channels
            if is_openchannel:
                feature['losses_Kentry'] = 0.0
                feature['losses_Kexit'] = 0.0
            else:
                if not has_upstream and not has_inlet_us:
                    feature['losses_Kentry'] = self.up_entrance_loss
                else:
                    feature['losses_Kentry'] = self.other_entrance_loss

                if not has_downstream and not has_inlet_ds:
                    feature['losses_Kexit'] = self.down_exit_loss
                else:
                    feature['losses_Kexit'] = self.other_exit_loss

            feature['losses_Kavg'] = 0.0
        except Exception as e:
            self.feedback.reportError(f'Error processing feature {feature["Name"]}.\n{str(e)}')

        return [feature]
