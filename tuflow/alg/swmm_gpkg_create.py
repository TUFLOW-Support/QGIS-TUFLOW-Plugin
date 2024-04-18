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
from tuflow_swmm.create_swmm_section_gpkg import add_swmm_section_to_gpkg, create_section_from_gdf
from tuflow_swmm.swmm_sections import swmm_section_definitions, GeometryType, SectionType
from tuflow_swmm.swmm_defaults import default_options_table, default_reporting_table, has_gpd
from tuflow_swmm.swmm_gdal import delete_layer_features
from tuflow_swmm.swmm_io import write_tuflow_version

import os

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


# Following pattern from https://docs.qgis.org/3.28/en/docs/user_manual/processing/scripts.html#:~:text=Within%20QGIS%2C%20you%20can%20use%20Create%20new%20script,menu.%20This%20opens%20a%20template%20that%20extends%20QgsProcessingAlgorithm.
class GeoPackageCreate(QgsProcessingAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def __init__(self):
        super().__init__()
        self.swmm_section_long_names = None
        self.swmm_section_names = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return GeoPackageCreate()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'CreateSWMMGeoPackage'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('GeoPackage - Create')

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
        help_filename = folder / 'help/html/alg_gpkg_create.html'
        return help_filename.read_text()

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        # 'INPUT' is the recommended name for the main input
        # parameter.
        self.addParameter(
            QgsProcessingParameterFileDestination(
                'INPUT_output_filename',
                self.tr('GPKG filename to create (temporary file not recommended)'),
                fileFilter='*.gpkg',
            )
        )

        self.addParameter(
            QgsProcessingParameterCrs(
                'INPUT_CRS',
                self.tr('CRS for GeoPackage'),
            )
        )

        swmm_sections = swmm_section_definitions()
        swmm_sections.sort(key=lambda x: x.long_name())

        sections_to_skip = {
            'Inlet_Usage_ext',
            'XSections',
            'Losses',
            'Subareas',
            'Infiltration',
            'Transects_coords',
            'Tags',
        }

        # filter out the sections we do not want to include
        swmm_sections = list(
            filter(
                lambda x:
                ((x.geometry is not None and x.geometry == GeometryType.MISC) or
                 (x.section_type != SectionType.GEOMETRY)) and
                x.name not in sections_to_skip,
                swmm_sections
            )
        )

        self.swmm_section_names = [x.name for x in swmm_sections]
        self.swmm_section_long_names = [x.long_name() for x in swmm_sections]

        default_options = [
            self.swmm_section_long_names.index(x) for x in [
                'Project--Title',
                'Project--Options',
                'Project--Report',
                'Nodes--Junctions',
                'Nodes--Outfalls',
                'Nodes--Storage',
                'Links--Conduits',
                'Links--Streets',
                'Inlets--Inlets',
                #'Inlet_Usage', Generally use external layer
            ]
        ]

        self.addParameter(
            QgsProcessingParameterEnum(
                'Input_initial_sections',
                self.tr('Initial SWMM Sections'),
                options=self.swmm_section_long_names,
                defaultValue=default_options,
                allowMultiple=True,
                usesStaticStrings=False,
            )
        )

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        self.addOutput(
            QgsProcessingOutputNumber(
                'NUMBER_OF_SECTIONS',
                'Number of sections added',
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

        gpkg_file = self.parameterAsFile(parameters,
                                         'INPUT_output_filename',
                                         context)

        # We are creating a new file
        if not Path(gpkg_file).exists():
            write_tuflow_version(gpkg_file)

        crs = self.parameterAsCrs(parameters,
                                  'INPUT_CRS',
                                  context)
        crs_text = crs.toWkt()

        sections = self.parameterAsEnums(
            parameters,
            'Input_initial_sections',
            context,
        )

        initial_names = [self.swmm_section_names[opt] for opt in sections]

        if 'Curves--Transects' in initial_names:
            initial_names.append('Transects_coords')

        layers_with_dummy_rows = []
        for name in initial_names:
            feedback.pushInfo(f'Adding {name}')
            if name == 'Report' or name == 'Options':
                gdf_default = None
                gdf_default_layername = None
                if name == 'Options':
                    gdf_default, gdf_default_layername = default_options_table(
                        crs_text,
                        '00:10:00',
                        25.0,
                    )
                else:
                    gdf_default, gdf_default_layername = default_reporting_table(
                        crs_text,
                    )

                gdf_default.to_file(gpkg_file,
                                    layer=gdf_default_layername,
                                    driver='GPKG')
            else:
                layers_with_dummy_rows.append(
                    add_swmm_section_to_gpkg(
                        gpkg_file,
                        name,
                        crs_text,
                    )
                )

        for name in layers_with_dummy_rows:
            delete_layer_features(gpkg_file, name)

        result_dict = {
            'OUTPUT': len(initial_names),
        }

        # Return the results
        return result_dict
