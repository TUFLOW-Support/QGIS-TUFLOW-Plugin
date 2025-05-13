import os

from qgis.PyQt.QtCore import QVariant, QCoreApplication
from qgis._core import QgsProcessingContext
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterFeatureSink
import processing
from qgis.core import (QgsWkbTypes, QgsProcessingUtils, QgsFeatureSink, QgsField, QgsFields, QgsSpatialIndex,
                       QgsProcessingException, QgsExpression, QgsFeatureRequest)

from ..mitools.perpendicular_lines import PerpendicularLines
from ..compatibility_routines import Path, QT_DOUBLE


class CreateWLL(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration = ...):
        # 1D network channel input
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'nwk_input',
                '1D Network Channel Layer',
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None
            )
        )
        # WLL line length
        self.addParameter(
            QgsProcessingParameterNumber(
                'wll_length',
                'WLL Line Length',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=10000,
                defaultValue=100)
        )
        # WLL Max Spacing
        self.addParameter(
            QgsProcessingParameterNumber(
                'wll_spacing',
                'WLL Max Spacing',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=10000,
                defaultValue=100)
        )
        # WLL Spacing Calculation Method
        self.addParameter(
            QgsProcessingParameterEnum(
                'wll_spacing_method',
                'WLL Spacing Calculation Method',
                options=['Fixed Spacing Along Channel Length', 'Equal Spacing Along Channel Length', 'Equal Spacing Along Channel Segment'],
                allowMultiple=False,
                defaultValue=1,
                usesStaticStrings=False
            )
        )
        # Always Add WLL at Vertices
        self.addParameter(
            QgsProcessingParameterBoolean(
                'wll_at_vertices',
                'Always Add WLL at Vertices',
                defaultValue=False
            )
        )
        # WLL clipping
        self.addParameter(
            QgsProcessingParameterBoolean(
                'clip_to_layer',
                'Clip WLLs to layer',
                defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'clip_layer',
                'Clip Layer',
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
                optional=True
            )
        )
        # WLL Thinning
        self.addParameter(
            QgsProcessingParameterEnum(
                'wll_thinning_method',
                'WLL Thinning Options_test',
                options=['No Thinning', 'Remove Overlapping WLLs', 'Remove Overlapping WLLs and WLLs close to Vertices'],
                allowMultiple=False,
                usesStaticStrings=False,
                defaultValue=1
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                'WLL Layer Output'
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # pass parameters to WLL Creation Class
        wll = PerpendicularLines()
        wll.lyr = self.parameterAsLayer(parameters, 'nwk_input', context)
        wll.crs = wll.lyr.crs()
        wll.attr_callback = lambda feat, geom, ind: feat.setAttributes([0.])
        wll.length = self.parameterAsDouble(parameters, 'wll_length', context)
        wll.spacing = self.parameterAsDouble(parameters, 'wll_spacing', context)
        spacing_method = self.parameterAsEnum(parameters, 'wll_spacing_method', context)
        if spacing_method == 0:
            wll.method = 'fixed_linestring'
        elif spacing_method == 1:
            wll.method = 'equal_linestring'
        elif spacing_method == 2:
            wll.method = 'equal_segment'
        wll.at_vertices = self.parameterAsBool(parameters, 'wll_at_vertices', context)
        if parameters['clip_to_layer']:
            wll.clip_lyr = self.parameterAsLayer(parameters, 'clip_layer', context)
            wll.clip_si = QgsSpatialIndex(wll.clip_lyr.getFeatures())
        thinning_method = self.parameterAsEnum(parameters, 'wll_thinning_method', context)
        if thinning_method == 0:
            wll.thinning = 'none'
        elif thinning_method == 1:
            wll.thinning = 'overlap'
        elif thinning_method == 2:
            wll.thinning = 'overlap_vertices'
        wll.middle_vertex = self.parameterAsBool(parameters, 'wll_middle_vertex', context)
        wll.validate()
        if wll.lyr_is_nwk_type:
            wll.exp = QgsExpression('"Type" NOT IN (\'X\', \'x\')')
            wll.si = QgsSpatialIndex(wll.lyr.getFeatures(QgsFeatureRequest(wll.exp)))
        else:
            wll.si = QgsSpatialIndex(wll.lyr.getFeatures())

        feedback = QgsProcessingMultiStepFeedback(wll.count_lines(), model_feedback)

        # setup output layer
        fields = QgsFields()
        fields.append(QgsField('Dist_for_A', type=QT_DOUBLE, len=15, prec=5))
        sink, dest_id = self.parameterAsSink(
            parameters,
            'OUTPUT',
            context,
            fields,
            QgsWkbTypes.LineString,
            wll.lyr.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, 'OUTPUT'))

        # create WLLs
        for feat in wll.iter():
            if feedback.isCanceled():
                return {}
            feedback.setCurrentStep(wll.total_steps)
            added = sink.addFeature(feat, QgsFeatureSink.FastInsert)
            if not added:
                feedback.reportError('Unable to add features to output')

        feedback.pushInfo(f'\nWLLs created: {wll.total_steps}')
        feedback.pushInfo(f'WLLs removed: {wll.nrem}')

        del sink  # forces it to write to disk if required (i.e. output is a file)
        output_layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
        if output_layer.storageType() == 'Memory storage':
            output_layer.setName('1d_WLL_output')

        # set layer - allows renaming if output is memory layer
        context.setLayersToLoadOnCompletion({
            output_layer.id(): QgsProcessingContext.LayerDetails(output_layer.name(), context.project(), output_layer.name())
        })
        return {'OUTPUT': output_layer}

    def name(self):
        return 'Create Water Level Lines'

    def displayName(self):
        return 'Create Water Level Lines'

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'create_wll.html'
        return self.tr(help_filename.open().read().replace('\n', '<p>'))

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return 'miTools'

    def groupId(self):
        return 'miTools'

    def createInstance(self):
        return CreateWLL()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
