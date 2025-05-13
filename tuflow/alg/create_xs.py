import os

import numpy as np
from qgis.PyQt.QtCore import QVariant, QCoreApplication
from qgis._core import QgsProcessingContext
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFeatureSink
import processing
from qgis.core import (QgsWkbTypes, QgsProcessingUtils, QgsFeatureSink, QgsField, QgsFields, QgsSpatialIndex,
                       QgsProcessingException, QgsExpressionContext, QgsExpression, QgsFeatureRequest, QgsRaster,
                       QgsGeometry, QgsCoordinateTransform, QgsCoordinateTransformContext)

from ..mitools.perpendicular_lines import PerpendicularLines
from ..compatibility_routines import Path
from ..utils.raster_geom import RasterGeometry
from tuflow.compatibility_routines import QT_STRING, QT_INT, QT_DOUBLE


def drape_line_on_raster(line_geom, line_crs, raster, context):
    raster_geom = RasterGeometry(raster)
    if line_crs.isValid() and raster.crs().isValid() and line_crs != raster.crs():
        line_geom_tr = QgsGeometry(line_geom)
        line_geom_tr.transform(QgsCoordinateTransform(line_crs, raster.crs(), context.project()))
    else:
        line_geom_tr = line_geom
    locs = raster_geom.points_along_linestring(line_geom_tr)
    xs = np.array([[ch, raster.dataProvider().identify(p, QgsRaster.IdentifyFormatValue).results()[1]] for ch, p in locs])
    if xs.any():
        xs = xs[~np.isnan(xs[:,1])]
    return xs

class CreateCrossSections(QgsProcessingAlgorithm):

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
        # Cross-Section Position
        self.addParameter(
            QgsProcessingParameterEnum(
                'xs_position',
                'Cross-Section Position',
                options=['At Ends', 'At Midpoints'],
                defaultValue=[0]
            )
        )
        # Cross-Section line length
        self.addParameter(
            QgsProcessingParameterNumber(
                'xs_length',
                'Cross-Section Line Length',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=10000,
                defaultValue=100)
        )
        # Cross-Section clipping
        self.addParameter(
            QgsProcessingParameterBoolean(
                'clip_to_layer',
                'Clip Cross-Sections to layer',
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
        self.addParameter(
            QgsProcessingParameterBoolean(
                'export_to_csv',
                'Export Cross-Sections to CSV',
                defaultValue=False
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                'csv_output_dir',
                'CSV Output Directory',
                defaultValue='',
                optional=True,
                behavior=QgsProcessingParameterFile.Folder
            )
        )
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                'drape_raster',
                'Elevation Raster',
                defaultValue=None,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                'Cross-Section Layer Output'
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # pass parameters to Cross-Section Creation Class
        xs_gen = PerpendicularLines()
        xs_gen.lyr = self.parameterAsLayer(parameters, 'nwk_input', context)
        xs_gen.crs = xs_gen.lyr.crs()
        xs_gen.length = self.parameterAsDouble(parameters, 'xs_length', context)
        xs_pos = self.parameterAsEnum(parameters, 'xs_position', context)
        if xs_pos == 1:
            xs_gen.at_midpoint = True
            xs_gen.at_ends = False
        if parameters['clip_to_layer']:
            xs_gen.clip_lyr = self.parameterAsLayer(parameters, 'clip_layer', context)
            xs_gen.clip_si = QgsSpatialIndex(xs_gen.clip_lyr.getFeatures())
        xs_gen.validate()
        if xs_gen.lyr_is_nwk_type:
            xs_gen.exp = QgsExpression('"Type" IN (\'S\', \'s\', \'G\', \'g\', \'\') OR "Type" IS NULL')
            xs_gen.si = QgsSpatialIndex(xs_gen.lyr.getFeatures(QgsFeatureRequest(xs_gen.exp)))
        else:
            xs_gen.si = QgsSpatialIndex(xs_gen.lyr.getFeatures())

        # some checks
        if parameters['export_to_csv'] and not parameters['drape_raster']:
            raise QgsProcessingException(
                'Export to CSV: Must specify a raster to extract elevations from'
            )
        out_dest = parameters['OUTPUT'].sink.valueAsString(QgsExpressionContext())[0]
        if parameters['export_to_csv'] and not parameters['csv_output_dir'] and out_dest == 'TEMPORARY_OUTPUT':
            raise QgsProcessingException(
                'Export to CSV: Must specify a CSV output directory or do not use a temporary output layer'
            )

        # output csv
        csv_dir = None
        csv_relpath = ''
        raster = self.parameterAsLayer(parameters, 'drape_raster', context)
        if parameters['export_to_csv']:
            if raster.crs().isValid() and xs_gen.lyr.crs().isValid() and raster.crs() != xs_gen.lyr.crs():
                model_feedback.pushWarning(
                    'WARNING: Input 1D network channel and input raster use different CRS, '
                    'coordinate transformation will be performed when cutting cross-sections'
                )
            if parameters['csv_output_dir']:
                csv_dir = Path(parameters['csv_output_dir'])
            else:
                if 'dbname=' in out_dest:
                    csv_dir = Path(out_dest.split('=')[1].strip('\'')).parent
                else:
                    csv_dir = Path(out_dest).parent
                csv_dir = csv_dir / 'csv'
            if not csv_dir.exists():
                csv_dir.mkdir()
            if out_dest != 'TEMPORARY_OUTPUT':
                try:
                    csv_relpath = os.path.relpath(csv_dir, Path(out_dest).parent)
                except ValueError:
                    pass

        feedback = QgsProcessingMultiStepFeedback(xs_gen.count_lines(), model_feedback)

        # setup output layer
        fields = QgsFields()
        fields.append(QgsField('Source', type=QT_STRING, len=50))
        fields.append(QgsField('Type', type=QT_STRING, len=2))
        fields.append(QgsField('Flags', type=QT_STRING, len=8))
        fields.append(QgsField('Column1', type=QT_STRING, len=20))
        fields.append(QgsField('Column2', type=QT_STRING, len=20))
        fields.append(QgsField('Column3', type=QT_STRING, len=20))
        fields.append(QgsField('Column4', type=QT_STRING, len=20))
        fields.append(QgsField('Column5', type=QT_STRING, len=20))
        fields.append(QgsField('Column6', type=QT_STRING, len=20))
        fields.append(QgsField('Z_Increment', type=QT_DOUBLE, len=15, prec=5))
        fields.append(QgsField('Skew', type=QT_DOUBLE, len=15, prec=5))
        sink, dest_id = self.parameterAsSink(
            parameters,
            'OUTPUT',
            context,
            fields,
            QgsWkbTypes.LineString,
            xs_gen.lyr.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, 'OUTPUT'))

        # setup callback that assigns attributes values
        def xs_attr_callback(feat, geom, ind, csv_relpath):
            csv_path = f'XS{ind:04d}.csv'
            if csv_relpath:
                csv_path = f'{csv_relpath}{os.sep}{csv_path}'
            feat.setAttributes([
                csv_path, 'XZ', '', '', '', '', '', '', '', 0., 0.
            ])
        xs_gen.attr_callback = lambda feat, geom, ind: xs_attr_callback(feat, geom, ind, csv_relpath)

        # create Cross-Sections
        for feat in xs_gen.iter():
            if feedback.isCanceled():
                return {}
            feedback.setCurrentStep(xs_gen.total_steps)
            added = sink.addFeature(feat, QgsFeatureSink.FastInsert)
            if not added:
                feedback.reportError('Unable to add features to output')
            # create csv
            if parameters['export_to_csv']:
                csv = csv_dir / Path(feat[0]).name
                drape = drape_line_on_raster(feat.geometry(), xs_gen.lyr.crs(), raster, context)
                np.savetxt(csv, drape, delimiter=',', header='X,Z', comments='', fmt='%.3f')
                if not drape.any():
                    feedback.pushWarning(f'WARNING: No raster values found for {Path(feat[0]).name}')

        feedback.pushInfo(f'\nCross-Sections created: {xs_gen.total_steps}')

        del sink  # forces it to write to disk if required (i.e. output is a file)
        output_layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
        if output_layer.storageType() == 'Memory storage':
            output_layer.setName('1d_xs_output')

        # set layer - allows renaming if output is memory layer
        context.setLayersToLoadOnCompletion({
            output_layer.id(): QgsProcessingContext.LayerDetails(output_layer.name(), context.project(), output_layer.name())
        })
        return {'OUTPUT': output_layer}

    def name(self):
        return 'Create Cross-Section Lines'

    def displayName(self):
        return 'Create Cross-Section Lines'

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'create_xs.html'
        return self.tr(help_filename.open().read().replace('\n', '<p>'))

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return 'miTools'

    def groupId(self):
        return 'miTools'

    def createInstance(self):
        return CreateCrossSections()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)