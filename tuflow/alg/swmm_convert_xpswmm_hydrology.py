from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsField,
                       QgsFields,
                       QgsGeometry,
                       QgsPoint,
                       QgsPointXY,
                       QgsPolygon,
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
from PyQt5.QtCore import QVariant

from osgeo import ogr, gdal

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from ..gui.logging import Logging

from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper
from tuflow.tuflow_swmm.convert_xpswmm_hydrology import convert_xpswmm_hydrology

has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    from pandas.api.types import is_integer_dtype, is_numeric_dtype

    has_gpd = True
except ImportError:
    pass  # defaulted to false


def geopandas_dtype_to_field_type(dtype):
    if is_integer_dtype(dtype):
        return QVariant.Int
    elif is_numeric_dtype(dtype):
        return QVariant.Double
    elif str(type(dtype)) == 'geometry':
        return None
    else:
        return QVariant.String


def extract_gdf_fields(gdf):
    fields = []
    for col, col_type in gdf.dtypes.items():
        if col == 'geometry':
            continue
        qvar = geopandas_dtype_to_field_type(col_type)
        if qvar is not None:
            fields.append(QgsField(col, qvar))

    return fields


def create_polygon_feature(row, new_layer, features_to_add, feedback):
    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsGeometry.fromWkt(row['geometry'].wkt)

    # validate_errors = new_geom.validateGeometry()
    # if validate_errors:
    #    print(f'Errors found converting {row["Name"]}: {validate_errors}')
    new_feat.setGeometry(new_geom)

    for q_field in new_layer.fields().toList():
        col = q_field.name()
        new_feat.setAttribute(col, row[col])

    features_to_add.append(new_feat)

    return None


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


class ConvertXPSWMMHydrology(QgsProcessingAlgorithm):
    """
    This processing tool converts XPSWMM hydrology output into a layer that contains additional information from
    XPSWMM node export that can be copied into the subcatchments layer (often infiltration parameters)
    """

    # This seemed to contribute to an issue
    # def __init__(self):
    #    super().__init__()

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ConvertXPSWMMHydrology()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TUFLOW_SWMMConvertXPSWMMHydrology'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Convert - XPSWMM Hydrology (Beta)')

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
        help_filename = folder / 'help/html/alg_convert_xpswmm_hydrology.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.mapLayerHelperSWMMSubcatchments = MapLayerParameterHelper()
        self.mapLayerHelperSWMMSubcatchments.setMapLayerType(QgsProcessing.TypeVectorPolygon)
        self.mapLayerHelperSWMMSubcatchments.setLayerFilter(lambda x: x.name().find('Hydrology--Subcatchments') != -1)
        self.mapLayerHelperSWMMSubcatchments.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_swmm_subcatchments',
                self.tr('Input SWMM subcatchment layers (named Hyrdrology--Subcatchments)'),
                self.mapLayerHelperSWMMSubcatchments.getMapLayerNames(),
                allowMultiple=False,
                optional=False,
            )
        )

        self.mapLayerHelperGISSubcatchments = MapLayerParameterHelper()
        self.mapLayerHelperGISSubcatchments.setMapLayerType(QgsProcessing.TypeVectorPolygon)
        self.mapLayerHelperGISSubcatchments.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_gis_subcatchments',
                self.tr('Input GIS Subcatchments (exported via XPSWMM right-click on subcatchments)'),
                self.mapLayerHelperGISSubcatchments.getMapLayerNames(),
                allowMultiple=False,
                optional=False,
            )
        )

        self.mapLayerHelperGISNodes = MapLayerParameterHelper()
        self.mapLayerHelperGISNodes.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperGISNodes.refreshLayers()

        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_gis_nodes',
                self.tr('Input GIS Nodes (exported via XPSWMM right-click on nodes)'),
                self.mapLayerHelperGISNodes.getMapLayerNames(),
                allowMultiple=False,
                optional=False,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_swmm_subcatch',
                self.tr('Output Subcatchments Layer')
            )
        )

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

        if not has_gpd:
            message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                       'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
            feedback.reportError(message, fatalError=True)

        lays_swmm_subcatch_pos = self.parameterAsEnums(parameters,
                                                       'INPUT_swmm_subcatchments',
                                                       context)
        lays_swmm_subcatch = self.mapLayerHelperSWMMSubcatchments.getLayersFromIndices(lays_swmm_subcatch_pos)
        lay_swmm_subcatch = lays_swmm_subcatch[0]

        lays_gis_subcatch_pos = self.parameterAsEnums(parameters,
                                                      'INPUT_gis_subcatchments',
                                                      context)
        lays_gis_subcatch = self.mapLayerHelperGISSubcatchments.getLayersFromIndices(lays_gis_subcatch_pos)
        lay_gis_subcatch = lays_gis_subcatch[0]

        lays_gis_nodes_pos = self.parameterAsEnums(parameters,
                                                   'INPUT_gis_nodes',
                                                   context)
        lays_gis_nodes = self.mapLayerHelperGISNodes.getLayersFromIndices(lays_gis_nodes_pos)
        lay_gis_nodes = lays_gis_nodes[0]

        gdf_swmm_subcatch = gpd.GeoDataFrame.from_features(lay_swmm_subcatch.getFeatures())
        self.feedback.pushInfo(f'Read {len(gdf_swmm_subcatch)} from {lay_swmm_subcatch.name()}')

        gdf_gis_subcatch = gpd.GeoDataFrame.from_features(lay_gis_subcatch.getFeatures())
        self.feedback.pushInfo(f'Read {len(gdf_gis_subcatch)} from {lay_gis_subcatch.name()}')

        gdf_gis_nodes = gpd.GeoDataFrame.from_features(lay_gis_nodes.getFeatures())
        self.feedback.pushInfo(f'Read {len(gdf_gis_nodes)} from {lay_gis_nodes.name()}')

        gdf_out_swmm_subcatch = convert_xpswmm_hydrology(
            gdf_gis_nodes,
            gdf_gis_subcatch,
            gdf_swmm_subcatch,
            gdf_swmm_subcatch.crs,
            feedback=self.feedback
        )

        out_fields = extract_gdf_fields(gdf_out_swmm_subcatch)

        qfields_out = QgsFields()
        for field in out_fields:
            qfields_out.append(field)

        out_sink_swmm_subcatch, out_layer_swmm_subcatch = self.parameterAsSink(
            parameters,
            'OUTPUT_swmm_subcatch',
            context,
            qfields_out,
            lay_swmm_subcatch.wkbType(),
            lay_swmm_subcatch.sourceCrs()
        )
        if isinstance(out_layer_swmm_subcatch, str):
            out_layer_swmm_subcatch = QgsProcessingUtils.mapLayerFromString(
                out_layer_swmm_subcatch,
                context)
        else:
            feedback.reportError('SWMM subcatchment output layer is inavlid.', fatalError=True)

        subcatchments_to_add = []
        gdf_out_swmm_subcatch.apply(
            lambda x: create_polygon_feature(x, out_layer_swmm_subcatch, subcatchments_to_add, feedback),
            axis=1)
        dp_subcatch = out_layer_swmm_subcatch.dataProvider()
        out_layer_swmm_subcatch.startEditing()
        dp_subcatch.addAttributes(out_fields)
        out_layer_swmm_subcatch.updateFields()
        self.feedback.pushInfo(f'Adding {len(subcatchments_to_add)} subcatchments to output layer')
        dp_subcatch.addFeatures(subcatchments_to_add)
        out_layer_swmm_subcatch.commitChanges()

        result_dict = {
            'OUTPUT': f'{out_layer_swmm_subcatch.name()}',
        }

        # Return the results
        return result_dict
