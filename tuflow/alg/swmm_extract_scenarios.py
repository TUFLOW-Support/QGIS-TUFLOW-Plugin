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
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFolderDestination,
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
from tuflow.tuflow_swmm.qgis.toc_swmm import find_swmm_gpkgs
from tuflow.tuflow_swmm.swmm_extract_scenarios import extract_scenarios

import os

has_gpd = False
try:
    import geopandas as gpd

    has_gpd = True
except ImportError:
    pass  # defaulted to false

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


# Following pattern from https://docs.qgis.org/3.28/en/docs/user_manual/processing/scripts.html#:~:text=Within%20QGIS%2C%20you%20can%20use%20Create%20new%20script,menu.%20This%20opens%20a%20template%20that%20extends%20QgsProcessingAlgorithm.
class SwmmExtractScenarios(QgsProcessingAlgorithm):
    """
    This processing tool creates SWMM GeoPackages for scenarios from multiple GPKG files.
    """

    def __init__(self):
        super().__init__()
        self.swmm_gpkgs = []
        self.swmm_gpkg_names = []

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return SwmmExtractScenarios()

    def flags(self):
        return QgsProcessingAlgorithm.Flag.FlagNoThreading

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'ExtractSWMMScenarios'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Scenarios - Extract from GPKGs')

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
        help_filename = folder / 'help/html/alg_swmm_extract_scenarios.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        #import pydevd_pycharm
        #pydevd_pycharm.settrace('localhost', port=53110, stdoutToServer=True, stderrToServer=True)

        self.swmm_gpkgs = find_swmm_gpkgs()
        self.swmm_gpkg_names = [Path(x).stem for x in self.swmm_gpkgs]

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_gpkg_names',
                self.tr('Source GeoPackages'),
                options=self.swmm_gpkg_names,
                defaultValue= [],#self.swmm_gpkg_names,#list(range(len(self.swmm_gpkgs))),
                allowMultiple=True,
                usesStaticStrings=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                'INPUT_output_folder',
                self.tr('Folder to Place Generated GPKGs'),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                'INPUT_output_prefix',
                self.tr('Prefix for Output GeoPackage Files'),
                defaultValue='proj',
            )
        )


    def processAlgorithm(self, parameters, context, feedback):
        """
        This is where the majic happens
        """
        self.feedback = feedback

        if not has_gpd:
            message = ('This tool requires geopandas: to install please follow instructions on the following webpage: '
                       'https://wiki.tuflow.com/QGIS_Intallation_with_OSGeo4W')
            feedback.reportError(message)
            return {}

        gpkg_positions = self.parameterAsEnums(
            parameters,
            'Input_gpkg_names',
            context,
        )
        feedback.pushInfo(str(gpkg_positions))
        gpkgs_to_use = [self.swmm_gpkgs[opt] for opt in gpkg_positions]

        output_folder = self.parameterAsFile(parameters,
                                         'INPUT_output_folder',
                                         context)
        output_path = Path(output_folder)
        output_path.mkdir(exist_ok=True)

        output_prefix = self.parameterAsString(parameters,
                                               'INPUT_output_prefix',
                                               context)

        generated_gpkgs = []

        feedback.pushInfo(str(gpkgs_to_use))
        feedback.pushInfo(f'\nScenarios to use:\n\t{"\n\t".join([str(x) for x in gpkgs_to_use])}')

        # from the geopackage files extract any common prefixes
        gpkg_names_to_use = [Path(x).stem for x in gpkgs_to_use]
        common_prefix = os.path.commonprefix(gpkg_names_to_use)
        feedback.pushInfo('\nRemoving common prefix {} from scenario names.\n'.format(common_prefix))

        scenario_names = [x[len(common_prefix):] for x in gpkg_names_to_use]
        feedback.pushInfo(f'\nScenario names:\n\t{"\n\t".join(scenario_names)}\n')

        output_control_file_lines = output_path / f'{output_prefix}_tscf_lines.txt'

        extract_scenarios(gpkgs_to_use,
                          scenario_names,
                          output_folder,
                          output_prefix,
                          output_control_file_lines,
                          feedback)

        result_dict = {
            'OUTPUT': generated_gpkgs,
        }

        # Return the results
        return result_dict
