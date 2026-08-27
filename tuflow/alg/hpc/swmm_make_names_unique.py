from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsExpressionContext,
                       QgsFeature,
                       QgsFeatureSink,
                       QgsFields,
                       QgsPointXY,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingException,
                       QgsProcessingOutputNumber,
                       QgsProcessingFeatureBasedAlgorithm,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterMultipleLayers,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingUtils,
                       QgsSpatialIndex)

from osgeo import ogr, gdal

# import processing
import tempfile

# from .swmmutil import copy_features

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path


# Following pattern from https://docs.qgis.org/3.28/en/docs/user_manual/processing/scripts.html#:~:text=Within%20QGIS%2C%20you%20can%20use%20Create%20new%20script,menu.%20This%20opens%20a%20template%20that%20extends%20QgsProcessingAlgorithm.
class MakeNamesUnique(QgsProcessingFeatureBasedAlgorithm):
    """
    This processing tool finds the nodes connected to conduits and reassigns the conduit
    'To Node' and 'From Node' appropriately.
    """

    def __init__(self):
        super().__init__()
        self.feedback = None
        self.previous_names = set()
        self.num_renamed = 0
        self.name_field = 'Name'
        self.tolerance = 0.001
        self.input_source = None

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        # Must return a new copy of your algorithm.
        return MakeNamesUnique()

    def name(self):
        """
        Returns the unique algorithm name.
        """
        return 'TuflowSWMMMakeNamesUnique'

    def displayName(self):
        """
        Returns the translated algorithm name.
        """
        return self.tr('Integrity - Make Object Names Unique')

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagSupportsInPlaceEdits | QgsProcessingAlgorithm.Flag.FlagNoThreading

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
        return self.tr('This algorithm adds a suffix (.#) to duplicately named SWMM features')

    def initParameters(self, config=None):
        """
        Here we define the inputs and outputs of the algorithm.
        """
        pass

        # 'OUTPUT' is the recommended name for the main output
        # parameter.
        # Done automatically
        #self.addParameter(
        #    QgsProcessingParameterFeatureSink(
        #        'OUTPUT',
        #        self.tr('Output Layer')
        #    )
        #)

        # self.addOutput(
        #    QgsProcessingOutputNumber(
        #        'NUMBER_OF_NAMECHANGES',
        #        self.tr('Number of names changed')
        #    )
        # )

    def outputName(self):
        return self.tr('CleanedObjects')

    def outputType(self):
        return QgsProcessing.TypeVectorAnyGeometry

    def outputWkbType(self, inputWkbType):
        return inputWkbType

    def prepareAlgorithm(self, parameters, context, feedback):
        """
        This is where the magic happens
        """
        self.feedback = feedback

        #self.input_source = self.parameterAsSource(parameters,
        #                                           'INPUT',
        #                                           context)

        # in constructor
        # self.n_renamed = 0
        # self.name_field = 'Name'
        # self.previous_names = set()

        return True

    def processFeature(self, feature, context, feedback):
        try:
            name = feature[self.name_field]
            # print(f'{feature.id()}:{name}')
            # if not in set add it and move to the next
            if name not in self.previous_names:
                self.previous_names.add(name)
            else:
                # find a unique name (add .#) until we are unique
                num_append = 2
                unique_name = f'{name}.{num_append}'
                while unique_name in self.previous_names:
                    num_append = num_append + 1
                    unique_name = f'{name}.{num_append}'
                # we found a unique name
                self.feedback.pushInfo(f'renaming {name} to {unique_name}')
                self.previous_names.add(unique_name)
                feature[self.name_field] = unique_name
                self.num_renamed = self.num_renamed + 1
        except:
            self.feedback.reportError(f'Error checking feature: {feature[self.name_field]}')

        return [feature]
