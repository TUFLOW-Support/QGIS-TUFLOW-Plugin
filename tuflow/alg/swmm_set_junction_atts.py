import itertools
import os
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsLayerTreeGroup,
                       QgsLayerTreeLayer,
                       QgsMapLayer,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputNumber,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterEnum,
                       QgsProcessingFeatureBasedAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterMapLayer,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterVectorLayer,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsProject,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

import tempfile
from toc.MapLayerParameterHelper import MapLayerParameterHelper

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.tuflow_swmm.set_junction_atts import get_junction_atts


class SetJunctionAtts(QgsProcessingFeatureBasedAlgorithm):
    """
    This processing tool assigns nodal attributes for junctions based upon SWMM and TUFLOW-SWMM conventions.
    """

    def __init__(self):
        super().__init__()
        self.feedback = None
        self.mapLayerHelperSubcatchments = None
        self.mapLayerHelperInletUsage = None
        self.mapLayerHelperBcConn = None
        self.df_atts = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return SetJunctionAtts()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMSetJunctionAtts'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Junctions - Set attributes')

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagSupportsInPlaceEdits

    def supportInPlaceEdit(self, layer):
        return True

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
        help_filename = folder / 'help/html/alg_set_junction_attributes.html'
        return help_filename.read_text()

    def initParameters(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        self.mapLayerHelperSubcatchments = MapLayerParameterHelper()
        self.mapLayerHelperSubcatchments.setMapLayerType(QgsProcessing.TypeVectorPolygon)
        self.mapLayerHelperSubcatchments.setLayerFilter(lambda x: x.name().find('Hydrology--Subcatchments') != -1)
        self.mapLayerHelperSubcatchments.refreshLayers()

        # Temp for testing
        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_subcatchments',
                self.tr('Input Subcatchment layers (named Hydrology--Subcatchments)'),
                self.mapLayerHelperSubcatchments.getMapLayerNames(),
                allowMultiple=True,
                optional=True,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterMultipleLayers(
        #         'INPUT_subcatchments',
        #         self.tr('Input Subcatchments'),
        #         layerType=QgsProcessing.TypeVectorPolygon,
        #         optional=True,
        #     )
        # )

        self.mapLayerHelperInletUsage = MapLayerParameterHelper()
        self.mapLayerHelperInletUsage.setMapLayerType(QgsProcessing.TypeVectorPoint)
        # self.mapLayerHelperInletUsage.setLayerFilter(lambda x: x.name().find('Hydrology--Subcatchments') != -1)
        self.mapLayerHelperInletUsage.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_inlet_usage',
                self.tr('Input Inlet Usage Layers'),
                self.mapLayerHelperInletUsage.getMapLayerNames(),
                allowMultiple=True,
                optional=True,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterMultipleLayers(
        #         'INPUT_inlet_usage',
        #         self.tr('Input Inlet Usage Layers'),
        #         layerType=QgsProcessing.TypeVectorPoint,
        #         optional=True,
        #     )
        # )

        self.mapLayerHelperBcConn = MapLayerParameterHelper()
        self.mapLayerHelperBcConn.setMapLayerType(QgsProcessing.TypeVectorLine)
        # self.mapLayerHelperInletUsage.setLayerFilter(lambda x: x.name().find('Hydrology--Subcatchments') != -1)
        self.mapLayerHelperBcConn.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_bc_conns',
                self.tr('Input BC Connection Layers'),
                self.mapLayerHelperBcConn.getMapLayerNames(),
                allowMultiple=True,
                optional=True,
            )
        )

        # self.addParameter(
        #     QgsProcessingParameterMultipleLayers(
        #         'INPUT_bc_conns',
        #         self.tr('Input BC Connection Layers'),
        #         layerType=QgsProcessing.TypeVectorAnyGeometry,
        #         optional=True,
        #     )
        # )

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_ymax_option',
                self.tr('<br><hr><b>General options</b><br><br>Maximum Depth Option (Ymax)'),
                options=['Set to 0.0',
                         'Leave as is (applies to edit in place only)'],
                allowMultiple=False,
                defaultValue='Set to 0.0'
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_subcatchment_option',
                self.tr('Nodes receiveing subcatchment flows option (if connected to 2D)'),
                options=[
                    'Based on options selected below',
                    'Set Apond = 0.0; Ysur = 0.0 (overwrites options below)',
                ],
                allowMultiple=False,
                defaultValue='Based on options selected below'
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_hx_ysur',
                self.tr('<br><hr><b>Nodes connected to 2D without inlets (through embankment culvert)</b><br><br>Ysur (recommended 0.0)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_hx_apond',
                self.tr('Apond (recommended typical area of connected cells)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_inlet_ymax_option',
                self.tr(
                    '<br><hr><b>Nodes connected to 2D with inlets (underground pipe network)</b><br><br>Maximum depth (Ymax) option (overwrites general setting)'),
                options=[
                    'Set to inlet elevation - node elevation',
                    'Use global option',
                ],
                allowMultiple=False,
                defaultValue='Set to inlet elevation - node elevation'
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_inlet_ysur',
                self.tr('Ysur'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_inlet_apond',
                self.tr('Area of ponding'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0.0,
            )
        )


        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_no_conn_ysur',
                self.tr('<br><hr><b>Nodes without a 2D connection (underground pipe network)</b><br><br>Surcharge depth (not used if apond > 0)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=50.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_no_conn_apond',
                self.tr('Area of ponding'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )

    def outputName(self):
        return self.tr('JunctionAtts')

    def outputType(self):
        return QgsProcessing.TypeVectorPoint

    def outputWkbType(self, inputWkbType):
        return inputWkbType

    def prepareAlgorithm(self, parameters, context, feedback):
        """
        This is where the magic happens
        """
        self.feedback = feedback

        input_source = self.parameterAsSource(parameters,
                                              'INPUT',
                                              context)

        lays_subcatch_pos = self.parameterAsEnums(parameters,
                                                  'Input_subcatchments',
                                                  context)
        lays_subcatch = self.mapLayerHelperSubcatchments.getLayersFromIndices(lays_subcatch_pos)

        # lays_subcatch = self.parameterAsLayerList(parameters,
        #                                          'Input_subcatchments',
        #                                          context)

        lays_inlet_usage_pos = self.parameterAsEnums(parameters,
                                                     'INPUT_inlet_usage',
                                                     context)
        lays_inlet_usage = self.mapLayerHelperInletUsage.getLayersFromIndices(lays_inlet_usage_pos)

        # lays_inlet_usage = self.parameterAsLayerList(parameters,
        #                                              'Input_inlet_usage',
        #                                              context)

        lays_bc_conn_pos = self.parameterAsEnums(parameters,
                                                     'INPUT_bc_conns',
                                                     context)
        lays_bc_conn = self.mapLayerHelperBcConn.getLayersFromIndices(lays_bc_conn_pos)

        # lays_bc_conn = self.parameterAsLayerList(parameters,
        #                                          'Input_bc_conns',
        #                                          context)

        initialize_ymax = self.parameterAsEnum(parameters,
                                               'Input_ymax_option',
                                               context) == 0

        subcatch_nodes_no_ponding = self.parameterAsEnum(parameters,
                                                         'Input_subcatchment_option',
                                                         context) == 1

        ymax_from_inlet_elev = self.parameterAsEnum(parameters,
                                                    'Input_inlet_ymax_option',
                                                    context) == 0

        inlet_ysur = self.parameterAsDouble(parameters,
                                            'Input_inlet_ysur',
                                            context)

        inlet_apond = self.parameterAsDouble(parameters,
                                             'Input_inlet_apond',
                                             context)

        hx_ysur = self.parameterAsDouble(parameters,
                                         'Input_hx_ysur',
                                         context)

        hx_apond = self.parameterAsDouble(parameters,
                                          'Input_hx_apond',
                                          context)

        no_conn_ysur = self.parameterAsDouble(parameters,
                                              'Input_no_conn_ysur',
                                              context)

        no_conn_apond = self.parameterAsDouble(parameters,
                                               'Input_no_conn_apond',
                                               context)

        if feedback.isCanceled():
            return {}

        self.df_atts = get_junction_atts(input_source.getFeatures(),
                                         lays_subcatch,
                                         lays_inlet_usage,
                                         lays_bc_conn,
                                         inlet_ysur,
                                         inlet_apond,
                                         hx_ysur,
                                         hx_apond,
                                         no_conn_ysur,
                                         no_conn_apond,
                                         initialize_ymax,
                                         subcatch_nodes_no_ponding,
                                         ymax_from_inlet_elev,
                                         self.feedback,
                                         )

        return True

    def processFeature(self, feature, context, feedback):
        try:
            ymax = self.df_atts.loc[self.df_atts['Name'] == feature['Name'], 'Ymax'].iloc[0]
            ysur = self.df_atts.loc[self.df_atts['Name'] == feature['Name'], 'Ysur'].iloc[0]
            apond = self.df_atts.loc[self.df_atts['Name'] == feature['Name'], 'Apond'].iloc[0]
            # If Ymax is null or not a number make 0.0
            try:
                feature['Ymax'] = float(ymax)
            except:
                feature['Ymax'] = 0.0
            feature['Ysur'] = float(ysur)
            feature['Apond'] = float(apond)
        except Exception as e:
            self.feedback.reportError(f'Unable to get data for feature {feature["Name"]}: {str(e)}')

        return [feature]
