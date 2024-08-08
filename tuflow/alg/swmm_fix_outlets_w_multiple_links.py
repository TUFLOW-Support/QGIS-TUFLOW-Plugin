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
                       QgsProcessingParameterCrs,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterString,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

# import processing
import tempfile

# from .swmmutil import copy_features
# from tuflow_swmm.swmm_to_gis import swmm_to_gpkg
from tuflow.tuflow_swmm.fix_multi_link_oulets import extend_multi_link_outfalls

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


# Following pattern from https://docs.qgis.org/3.28/en/docs/user_manual/processing/scripts.html#:~:text=Within%20QGIS%2C%20you%20can%20use%20Create%20new%20script,menu.%20This%20opens%20a%20template%20that%20extends%20QgsProcessingAlgorithm.
class SwmmFixOutletsMuliLinks(QgsProcessingAlgorithm):
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
        return SwmmFixOutletsMuliLinks()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'SwmmFixOutletsMuliLinks'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Outfalls - Fix Multiply Connected Links')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return self.tr('SWMM Tools')

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
        help_filename = folder / 'help/html/alg_fix_outlets_w_multiple_links.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFile(
                'INPUT',
                self.tr('GeoPackage in TUFLOW-SWMM Format'),
                extension='gpkg',
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                'INPUT_channel_ext_length',
                self.tr('Channel extension length'),
                defaultValue=10.0,
                minValue=0.001,
                optional=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                'INPUT_gpkg_output_filename',
                self.tr('GeoPackage output filename'),
                fileFilter='*.gpkg',
            )
        )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addOutput(
            QgsProcessingOutputFile(
                'OUTPUT',
                self.tr('GeoPackage output filename')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        input_filename = self.parameterAsFile(parameters,
                                              'INPUT',
                                              context)

        channel_ext_length = self.parameterAsDouble(
            parameters,
            'INPUT_channel_ext_length',
            context
        )

        output_filename = self.parameterAsFile(parameters,
                                               'INPUT_gpkg_output_filename',
                                               context)

        extend_multi_link_outfalls(input_filename,
                                   output_filename,
                                   channel_ext_length,
                                   feedback=self.feedback)

        # feedback.pushInfo(f'Finished writing: {output_filename}')

        result_dict = {
            'OUTPUT': output_filename,
        }

        # Return the results
        return result_dict
