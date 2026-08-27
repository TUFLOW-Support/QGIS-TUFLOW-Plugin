import os
import sys
import traceback

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
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsSpatialIndex)
from qgis.core import QgsMessageLog, QgsFeatureRequest, QgsWkbTypes

from osgeo import ogr, gdal

import geopandas as gpd

import tempfile

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper
from tuflow.tuflow_swmm.classify_inlets import process_gdb
from tuflow.geopandas.gpd_to_layer import fill_layer_from_gdf
from tuflow.toc.toc import tuflowqgis_find_layer


class ClassifySWMMInlets(QgsProcessingAlgorithm):
    """
    This processing tool takes an inlet usage layer and reclassifies the placement (on-sag vs on-grade) based on extracted DEM elevations with the direction
    based on a roadway layer.
    """

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ClassifySWMMInlets()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMClassifyInlets'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Inlets - Classify (on-sag vs on-grade)')

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
        help_filename = folder / 'help/html/alg_classify_inlets.html' # type: ignore
        return help_filename.read_text() # type: ignore

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # print(config)
        # 'INPUT' is the recommended name for the main input
        # parameter.
        # self.addParameter(
        #    QgsProcessingParameterFeatureSource(
        #        'INPUT',
        #        self.tr('Input Conduits Layer'),
        #        types=[QgsProcessing.TypeVector]
        #    )
        # )

        # Change to layer and selection toggle so we can get the full layer
        self.mapLayerHelperInlets = MapLayerParameterHelper()
        self.mapLayerHelperInlets.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperInlets.refreshLayers()

        self.mapLayerInletsParam = QgsProcessingParameterEnum(
            'INPUT_inlets',
            self.tr('Input Inlets Layer'),
            self.mapLayerHelperInlets.getMapLayerNames(),
            allowMultiple=False,
            optional=False,
        )
        self.addParameter(self.mapLayerInletsParam)
        self.mapLayerInletsParam.setOptions(self.mapLayerHelperInlets.getMapLayerNames())

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'Input_DEM',
                description='DEM to extract elevations from',
                defaultValue=None,
                optional=False
            )
        )

        self.mapLayerHelperRoads = MapLayerParameterHelper()
        self.mapLayerHelperRoads.setMapLayerType(QgsProcessing.TypeVectorLine)
        self.mapLayerHelperRoads.refreshLayers()

        self.mapLayerRoadsParam = QgsProcessingParameterEnum(
            'INPUT_roads',
            self.tr('Input Roads Layer'),
            self.mapLayerHelperRoads.getMapLayerNames(),
            allowMultiple=False,
            optional=False,
        )
        self.addParameter(self.mapLayerRoadsParam)
        self.mapLayerRoadsParam.setOptions(self.mapLayerHelperRoads.getMapLayerNames())

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_sample_distance',
                self.tr('Sample distance (each side)'),
                parentParameterName='INPUT_inlets',
                defaultValue=50.0,
                minValue=0.0,
                maxValue=10000.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'Input_number_of_values_to_extract',
                self.tr('Number of elevation values to extract (each side of inlet):'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=10,
                minValue=0,
                maxValue=1000,
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_max_road_distance',
                self.tr('Maximum distance to nearest road'),
                parentParameterName='INPUT_inlets',
                defaultValue=100.0,
                minValue=0.0,
                maxValue=10000.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_sag_tolerance',
                self.tr('Minimum rise from low-point to each side for on-sag inlets:'),
                parentParameterName='INPUT_inlets',
                defaultValue=0.2,
                minValue=0.0,
                maxValue=10000.0,
            )
        )


        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_sx_offset',
                self.tr('Offset Distance for BC line:'),
                defaultValue=1.0,
                minValue=0.0,
                maxValue=1000.0,
                parentParameterName='INPUT_inlets',
            )
        )

        self.addParameter(
            QgsProcessingParameterDistance(
                'Input_sx_reverse_distance',
                self.tr('Distance for BC line behind inlet:'),
                defaultValue=5.0,
                minValue=0.0,
                maxValue=1000.0,
                parentParameterName='INPUT_inlets',
            )
        )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_inlets_mod',
                self.tr('Modified TUFLOW-SWMM Inlet Usage Layer')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_bc',
                self.tr('2d_bc for On-Grade Connections')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_check_points',
                self.tr('Check Layer - Points')
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorDestination(
                'OUTPUT_check_extracted_section',
                self.tr('Check Layer - Cross-sections'),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback
        result_dict = {}

        try:
            inlets_layer_pos = self.parameterAsEnum(parameters,
                                                    'Input_inlets',
                                                    context)
            inlets_layer_name = self.mapLayerInletsParam.options()[inlets_layer_pos]
            inlets_layer = self.mapLayerHelperInlets.getLayersFromNames([inlets_layer_name])[0]
            self.feedback.pushInfo(f'Inlets layer name: {inlets_layer_name}')

            dem_layer = self.parameterAsRasterLayer(parameters, 'Input_DEM', context)
            dem_path = dem_layer.source()
            self.feedback.pushInfo(f'DEM location: {dem_path}')

            roads_layer_pos = self.parameterAsEnum(parameters,
                                                    'Input_roads',
                                                    context)
            roads_layer_name = self.mapLayerRoadsParam.options()[roads_layer_pos]
            roads_layer = self.mapLayerHelperRoads.getLayersFromNames([roads_layer_name])[0]
            self.feedback.pushInfo(f'Roads layer name: {roads_layer_name}')

            sample_distance = self.parameterAsDouble(parameters,
                                                    'INPUT_sample_distance',
                                                    context)
            self.feedback.pushInfo(f'\nSample distance: {sample_distance}')
            
            max_road_distance = self.parameterAsDouble(parameters,
                                                'INPUT_max_road_distance',
                                                context)
            self.feedback.pushInfo(f'Maximum road distance: {max_road_distance}')
            
            sag_tolerance = self.parameterAsDouble(parameters,
                                                'INPUT_sag_tolerance',
                                                context)
            self.feedback.pushInfo(f'Minimum Sag Elevation Rise: {sag_tolerance}')
            
            num_to_extract = self.parameterAsInt(parameters,
                                                    'Input_number_of_values_to_extract',
                                                    context)
            self.feedback.pushInfo(f'Number of values to extract each side: {num_to_extract}')
            
            sx_offset = self.parameterAsDouble(parameters,
                                                'INPUT_sx_offset',
                                                context)
            self.feedback.pushInfo(f'BC line offset: {sx_offset}')
            
            sx_reverse_distance = self.parameterAsDouble(parameters,
                                                'INPUT_sx_reverse_distance',
                                                context)
            self.feedback.pushInfo(f'BC line extend behind inlet: {sx_reverse_distance}')

            inlet_features = list(inlets_layer.getFeatures())
            self.feedback.pushInfo(f'Number of inlets: {len(inlet_features)}')
            gdf_inlets = gpd.GeoDataFrame.from_features(inlet_features)
            gdf_inlets = gdf_inlets.set_crs(inlets_layer.crs().toWkt())
            self.feedback.pushInfo(f'Number of inlets: {len(gdf_inlets)}')

            # Converting from QGIS was too slow. Try reading using GeoPandas
            parts = roads_layer.source().split('|')
            road_layer_file = parts[0]
            road_layername = None
            if len(parts) > 1:
                road_layername = parts[1]
                split_equals = road_layername.split('=')
                if len(split_equals) == 2:
                    road_layername = split_equals[1]
            gdf_roads = gpd.read_file(road_layer_file, layer=road_layername, columns=['geometry'])

            #self.feedback.pushInfo(f'Roads source: {roads_layer.source()}')            
            #self.feedback.pushInfo(f'Roads layer: {roads_layer}')
            #request_no_attributes = QgsFeatureRequest().setSubsetOfAttributes([], roads_layer.fields()) # we only need geometry
            #road_features = list(roads_layer.getFeatures(request_no_attributes))
            #self.feedback.pushInfo(f'Number of roads: {len(road_features)}')
            #gdf_roads = gpd.GeoDataFrame.from_features(road_features)


            self.feedback.pushInfo(f'Number of roads: {len(gdf_roads)}')

            check_xs_path = self.parameterAsOutputLayer(parameters, 'OUTPUT_check_extracted_section', context)
            check_xs_layername = None
            if check_xs_path.find('|') != -1:
                check_xs_path, check_xs_layername = check_xs_path.split('|')
                if check_xs_layername != "":
                    split_equals = check_xs_layername.split('=')
                    if len(split_equals) == 2:
                        check_xs_layername = split_equals[1]

            self.feedback.pushInfo(f'Output path for extracted sections: {check_xs_path}')

            csv_folder = Path(check_xs_path).parent / 'csv'
            self.feedback.pushInfo(f'Folder for csv files: {csv_folder}')

            process_result = process_gdb(
                dem_path,
                gdf_inlets,
                gdf_roads,
                sample_distance,
                max_road_distance,
                sag_tolerance,
                num_to_extract,
                sx_reverse_distance,
                sx_offset,
                csv_folder,
                self.feedback
            )

            # Primary output - modified inlets
            output_inlets_sink, output_inlets_layer = self.parameterAsSink(
                parameters,
                'OUTPUT_inlets_mod',
                context,
                QgsFields(),
                inlets_layer.wkbType(),
                inlets_layer.sourceCrs(),
            )
            if isinstance(output_inlets_layer, str):
                output_inlets_layer = QgsProcessingUtils.mapLayerFromString(
                    output_inlets_layer,
                    context)
            process_result.gdf_inlets_mod = process_result.gdf_inlets_mod.round(4)
            fill_layer_from_gdf(output_inlets_layer, process_result.gdf_inlets_mod)
            
            # BC connections for On Grade inlets
            if process_result.gdf_bcs is not None:
                output_bc_sink, output_bc_layer = self.parameterAsSink(
                    parameters,
                    'OUTPUT_bc',
                    context,
                    QgsFields(),
                    QgsWkbTypes.LineString,
                    inlets_layer.sourceCrs(),
                )
                if isinstance(output_bc_layer, str):
                    output_bc_layer = QgsProcessingUtils.mapLayerFromString(
                        output_bc_layer,
                        context)
                fill_layer_from_gdf(output_bc_layer, process_result.gdf_bcs)
            else:
                output_bc_layer = None
            

            # Check file - points
            output_check_points, output_check_point_layer = self.parameterAsSink(
                parameters,
                'OUTPUT_check_points',
                context,
                QgsFields(),
                inlets_layer.wkbType(),
                inlets_layer.sourceCrs(),
            )
            if isinstance(output_check_point_layer, str):
                output_check_point_layer = QgsProcessingUtils.mapLayerFromString(
                    output_check_point_layer,
                    context)
            
            process_result.gdf_check_points = process_result.gdf_check_points.round(4)
            fill_layer_from_gdf(output_check_point_layer, process_result.gdf_check_points)

            # Check file - 1d_xs - must have a path so we can write csv folder
            process_result.gdf_check_xs.to_file(check_xs_path, layer=check_xs_layername)

            result_dict = {
                'OUTPUT_inlets': output_inlets_layer,
                'OUTPUT_bc': output_bc_layer,
                'OUTPUT_check_point': output_check_point_layer,
                'OUTPUT_check_xs': check_xs_path,
            }

        except Exception as ex:
            try:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                message = ''.join(traceback.extract_tb(exc_traceback).format()) + '{0}{1}'.format(exc_type, exc_value)
                message = 'ERROR - Error classifying SWMM inlets: ' + '\n' + message
            except:
                message = 'ERROR - Error classifying SWMM inlets: ' + '\n' + str(ex)
            self.feedback.reportError(message, True)
        
        return result_dict


        # selected_only = self.parameterAsBoolean(parameters,
        #                                         'Input_selected_features_only',
        #                                         context)

        # location_option = int(self.parameterAsString(
        #     parameters,
        #     'Input_location_option',
        #     context,
        # ))
        # create_upstream = location_option != 2
        # create_downstream = location_option != 1

        # if create_upstream:
        #     feedback.pushInfo('Creating upstream segments.')

        # if create_downstream:
        #     feedback.pushInfo('Creating downstream segments.')

        # offset_dist = self.parameterAsDouble(parameters,
        #                                      'Input_offset_distance',
        #                                      context)

        # width = self.parameterAsDouble(parameters,
        #                                'Input_bc_length',
        #                                context)

        # set_z_flag = self.parameterAsBool(parameters,
        #                                   'Input_set_z_flag',
        #                                   context)

        # output_sink, output_layer = self.parameterAsSink(
        #     parameters,
        #     'OUTPUT',
        #     context,
        #     QgsFields(),
        #     source_layer.wkbType(),
        #     source_layer.sourceCrs(),
        # )
        # if isinstance(output_layer, str):
        #     output_layer = QgsProcessingUtils.mapLayerFromString(
        #         output_layer,
        #         context)

        # if feedback.isCanceled():
        #     return {}

        # layer_features = list(source_layer.getFeatures())
        # if selected_only:
        #     input_source = source_layer.getSelectedFeatures()
        # else:
        #     input_source = layer_features

        # create_endpoint_connections(input_source,
        #                             layer_features,
        #                             offset_dist,
        #                             width,
        #                             set_z_flag,
        #                             output_layer,
        #                             create_upstream,
        #                             create_downstream,
        #                             self.feedback,
        #                             )

        # result_dict = {
        #     'OUTPUT': output_layer,
        # }

        # Return the results
        # return None
