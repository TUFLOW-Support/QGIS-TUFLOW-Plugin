from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsField,
                       QgsFields,
                       QgsPoint,
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
from qgis.PyQt.QtCore import QVariant

from osgeo import ogr, gdal

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from ..gui.logging import Logging

from tuflow.toc.MapLayerParameterHelper import MapLayerParameterHelper
from tuflow.tuflow_swmm.junctions_to_storage import junctions_to_storage

has_gpd = False
try:
    import pandas as pd
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

from tuflow.compatibility_routines import QT_DOUBLE, QT_STRING, QT_INT


def create_feature(row, new_layer, features_to_add):
    new_feat = QgsFeature(new_layer.fields())
    new_geom = QgsPoint(row['geometry'].coords[0][0],
                        row['geometry'].coords[0][1])

    # validate_errors = new_geom.validateGeometry()
    # if validate_errors:
    #    print(f'Errors found converting {row["Name"]}: {validate_errors}')
    new_feat.setGeometry(new_geom)

    for q_field in new_layer.fields().toList():
        col = q_field.name()
        if col != 'fid':
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


class ConvertJunctionsToStorage(QgsProcessingAlgorithm):
    """
    This processing tool converts junctions to storage nodes for correct representation and stability.
    """

    # This seemed to contribute to an issue
    # def __init__(self):
    #    super().__init__()
    #    self.mapLayerHelperBcConn = None
    #    self.mapLayerHelperJunctions = None
    #    self.shape_text = []

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return ConvertJunctionsToStorage()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TUFLOW_SWMMConvertJunctionsStorage'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Junctions - Convert HX Nodes to Storage')

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
        help_filename = folder / 'help/html/alg_convert_junctions_to_storage.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.mapLayerHelperJunctions = MapLayerParameterHelper()
        self.mapLayerHelperJunctions.setMapLayerType(QgsProcessing.TypeVectorPoint)
        self.mapLayerHelperJunctions.setLayerFilter(lambda x: x.name().find('Nodes--Junctions') != -1)
        self.mapLayerHelperJunctions.refreshLayers()

        # Temp for testing
        self.addParameter(
            QgsProcessingParameterEnum(
                'INPUT_junctions',
                self.tr('Input Junction layers (named Nodes--Junctions)'),
                self.mapLayerHelperJunctions.getMapLayerNames(),
                allowMultiple=False,
                optional=True,
            )
        )

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

        self.shape_text = [
            'Pyramidal',
            'Cylindrical',
            'Conical',
        ]
        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_storage_shape',
                self.tr('Storage Shape'),
                self.shape_text,
                allowMultiple=False,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_storage_length',
                self.tr('Length (rectangular)/Major Axis (cylindrical/conical)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=20.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_storage_width',
                self.tr('Width (rectangular)/Minor Axis (cylindrical/conical)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=10.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_storage_z',
                self.tr('Inverse slope (run/rise) (only used for Pyramidal or Conical)'),
                QgsProcessingParameterNumber.Double,
                defaultValue=0.0,
                minValue=0.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_junctions',
                self.tr('Output Junctions Layer')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT_storage',
                self.tr('Output Storage Layer')
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

        lays_junctions_pos = self.parameterAsEnums(parameters,
                                                   'INPUT_junctions',
                                                   context)
        lays_junctions = self.mapLayerHelperJunctions.getLayersFromIndices(lays_junctions_pos)

        lays_bc_pos = self.parameterAsEnums(parameters,
                                            'INPUT_bc_conns',
                                            context)
        lays_bc = self.mapLayerHelperBcConn.getLayersFromIndices(lays_bc_pos)

        shape_option = self.shape_text[self.parameterAsEnum(
            parameters,
            'Input_storage_shape',
            context,
        )]

        length = self.parameterAsDouble(parameters,
                                        'Input_storage_length',
                                        context)
        width = self.parameterAsDouble(parameters,
                                       'Input_storage_width',
                                       context)

        z = self.parameterAsDouble(parameters,
                                   'Input_storage_z',
                                   context)

        if len(lays_junctions) == 0:
            feedback.reportError('Junction layer must be provided', fatalError=True)
        elif len(lays_junctions) > 1:
            feedback.reportError('Only one junction layer allowed', fatalError=True)

        lay_junction = lays_junctions[0]

        for lay_bc in lays_bc:
            feedback.pushInfo(f'BC Layer: {lay_bc.name()}')

        feedback.pushInfo(f'Shape: {shape_option}')
        feedback.pushInfo(f'Length (rectangular)/Major Axis (cylindrical/conical): {length}')
        feedback.pushInfo(f'Width (rectangular)/Minor Axis (cylindrical/conical): {width}')
        feedback.pushInfo(f'Slope inverse: {z}')

        gdf_junctions = gpd.GeoDataFrame.from_features(lay_junction.getFeatures())

        gdf_bc_conn = None
        gdfs_bc_conn = [gpd.GeoDataFrame.from_features(x.getFeatures()) for x in lays_bc]
        if len(gdfs_bc_conn) > 0:
            gdf_bc_conn = pd.concat(gdfs_bc_conn, axis=0, ignore_index=True)

        gdf_out_junctions, gdf_out_storage = junctions_to_storage(
            gdf_junctions,
            gdf_bc_conn,
            shape_option,
            length,
            width,
            z,
            feedback
        )

        out_sink_junctions, out_layer_junctions = self.parameterAsSink(
            parameters,
            'OUTPUT_junctions',
            context,
            lay_junction.fields(),
            lay_junction.wkbType(),
            lay_junction.sourceCrs()
        )
        if isinstance(out_layer_junctions, str):
            out_layer_junctions = QgsProcessingUtils.mapLayerFromString(
                out_layer_junctions,
                context)
        else:
            feedback.reportError('Junction output layer is inavlid.', fatalError=True)

        junctions_to_add = []
        gdf_out_junctions.apply(lambda x: create_feature(x, out_layer_junctions, junctions_to_add),
                                axis=1)
        dp_junctions = out_layer_junctions.dataProvider()
        out_layer_junctions.startEditing()
        dp_junctions.addAttributes([
            QgsField("Name", QT_STRING),
            QgsField("Elev", QT_DOUBLE),
            QgsField("Ymax", QT_DOUBLE),
            QgsField("Y0", QT_DOUBLE),
            QgsField("Ysur", QT_DOUBLE),
            QgsField("Apond", QT_DOUBLE),
        ])
        out_layer_junctions.updateFields()
        dp_junctions.addFeatures(junctions_to_add)
        out_layer_junctions.commitChanges()

        storage_fields = [
            QgsField("Name", QT_STRING),
            QgsField("Elev", QT_DOUBLE),
            QgsField("Ymax", QT_DOUBLE),
            QgsField("Y0", QT_DOUBLE),
            QgsField("TYPE", QT_STRING),
            QgsField("Acurve", QT_STRING),
            QgsField("A1", QT_DOUBLE),
            QgsField("A2", QT_DOUBLE),
            QgsField("A0", QT_DOUBLE),
            QgsField("L", QT_DOUBLE),
            QgsField("W", QT_DOUBLE),
            QgsField("Z", QT_DOUBLE),
            QgsField("Ysur", QT_DOUBLE),
            QgsField("Fevap", QT_DOUBLE),
            QgsField("Psi", QT_DOUBLE),
            QgsField("Ksat", QT_DOUBLE),
            QgsField("IMD", QT_DOUBLE),
            QgsField("Tag", QT_STRING),
            QgsField("Description", QT_STRING),
        ]
        qfields_storage = QgsFields()
        for field in storage_fields:
            qfields_storage.append(field)
        out_sink_storage, out_layer_storage = self.parameterAsSink(
            parameters,
            'OUTPUT_storage',
            context,
            qfields_storage,
            lay_junction.wkbType(),
            lay_junction.sourceCrs()
        )
        if isinstance(out_layer_storage, str):
            out_layer_storage = QgsProcessingUtils.mapLayerFromString(
                out_layer_storage,
                context)
        else:
            feedback.reportError('Storage node output layer is inavlid.', fatalError=True)

        storage_nodes_to_add = []
        gdf_out_storage.apply(lambda x: create_feature(x, out_layer_storage, storage_nodes_to_add),
                              axis=1)
        dp_storage = out_layer_storage.dataProvider()
        out_layer_storage.startEditing()
        dp_storage.addAttributes(storage_fields)
        out_layer_storage.updateFields()
        dp_storage.addFeatures(storage_nodes_to_add)
        out_layer_storage.commitChanges()

        result_dict = {
            'OUTPUT': f'',
        }

        # Return the results
        return result_dict
