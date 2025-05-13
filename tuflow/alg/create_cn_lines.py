import os

import numpy as np
from qgis._core import QgsExpression, QgsSpatialIndex, QgsFeatureRequest, QgsProcessingException, QgsFields, QgsField, \
    QgsWkbTypes, QgsFeatureSink, QgsProcessingContext, QgsProcessingUtils, QgsGeometry, QgsFeature, QgsPoint, QgsPointXY
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterFeatureSink
import processing

from qgis.PyQt.QtCore import QCoreApplication, QVariant

from ..compatibility_routines import QT_DOUBLE, Path, QT_STRING, QT_INT
from ..mitools.perpendicular_lines import PerpendicularLines
from ..tuflowqgis_library import is2dBCLayer


class CreateCNLines(QgsProcessingAlgorithm):

    def initAlgorithm(self, configuration = ...):
        # input 1d channel
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'nwk_lyr',
                '1D Network Channel Layer',
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None
            )
        )
        # code polygon
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'code_lyr',
                '1D Domain Code Polygon',
                types=[QgsProcessing.TypeVectorPolygon],
                defaultValue=None,
                optional=True
            )
        )
        # HX lines
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                'hx_lyr',
                'HX Lines',
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None,
                optional=True
            )
        )
        # max cn line length
        self.addParameter(
            QgsProcessingParameterNumber(
                'cn_length',
                'Max CN Line Length',
                type=QgsProcessingParameterNumber.Double,
                minValue=0,
                maxValue=10000,
                defaultValue=100)
        )
        # output
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                'OUTPUT',
                'CN Lines',
                type=QgsProcessing.TypeVectorLine
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        # pass parameters to perpendicular lines generator
        results = {}
        nwk_lyr = self.parameterAsVectorLayer(parameters, 'nwk_lyr', context)
        code_lyr = self.parameterAsVectorLayer(parameters, 'code_lyr', context)
        hx_lyr = self.parameterAsVectorLayer(parameters, 'hx_lyr', context)
        if code_lyr and hx_lyr:
            model_feedback.pushWarning('Both code and HX layers specified. Using HX layer.')
        if not code_lyr and not hx_lyr:
            clip_lyr = None
        if code_lyr or hx_lyr:
            clip_lyr = hx_lyr if hx_lyr else code_lyr
        cn_gen = PerpendicularLines()
        cn_gen.lyr = nwk_lyr
        cn_gen.length = self.parameterAsDouble(parameters, 'cn_length', context)
        cn_gen.attr_callback = lambda f, g, i: f.setAttributes(['CN', '', '', 0., 0., 0., 0., 0.])
        cn_gen.validate()
        if cn_gen.lyr_is_nwk_type:
            cn_gen.exp = QgsExpression('"Type" IN (\'S\', \'s\', \'G\', \'g\', \'\') OR "Type" IS NULL')
            cn_gen.si = QgsSpatialIndex(cn_gen.lyr.getFeatures(QgsFeatureRequest(cn_gen.exp)))
        else:
            cn_gen.si = QgsSpatialIndex(cn_gen.lyr.getFeatures())
        cn_gen.crs = cn_gen.lyr.crs()
        if clip_lyr:
            cn_gen.clip_lyr = clip_lyr
            clip_is_2d_bc = False
            if clip_lyr == hx_lyr and is2dBCLayer(hx_lyr):
                clip_is_2d_bc = True
                exp = QgsExpression('"Type" IN (\'HX\', \'Hx\', \'hx\', \'\') OR "Type" IS NULL')
                cn_gen.clip_si = QgsSpatialIndex(cn_gen.clip_lyr.getFeatures(QgsFeatureRequest(exp)))
            else:
                cn_gen.clip_si = QgsSpatialIndex(cn_gen.clip_lyr.getFeatures())

        feedback = QgsProcessingMultiStepFeedback(cn_gen.count_lines(), model_feedback)

        # setup output layers
        fields = QgsFields()
        fields.append(QgsField('Type', type=QT_STRING, len=2))
        fields.append(QgsField('Flags', type=QT_STRING, len=3))
        fields.append(QgsField('Name', type=QT_STRING, len=100))
        fields.append(QgsField('f', type=QT_DOUBLE, len=15, prec=5))
        fields.append(QgsField('d', type=QT_DOUBLE, len=15, prec=5))
        fields.append(QgsField('td', type=QT_DOUBLE, len=15, prec=5))
        fields.append(QgsField('a', type=QT_DOUBLE, len=15, prec=5))
        fields.append(QgsField('b', type=QT_DOUBLE, len=15, prec=5))
        sink, dest_id = self.parameterAsSink(
            parameters,
            'OUTPUT',
            context,
            fields,
            QgsWkbTypes.LineString,
            cn_gen.lyr.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, 'OUTPUT'))

        # modified clip layer with added vertices
        if clip_lyr:
            sink2, dest_id2 = QgsProcessingUtils.createFeatureSink(
                f'memory:'.format(clip_lyr.name()),
                context,
                clip_lyr.fields(),
                clip_lyr.wkbType(),
                clip_lyr.sourceCrs()
            )
            for feat in clip_lyr.getFeatures():
                sink2.addFeature(feat, QgsFeatureSink.FastInsert)
            del sink2
            clip_lyr_mod = QgsProcessingUtils.mapLayerFromString(dest_id2, context)
            clip_lyr_mod.setName('{0}_modified'.format(clip_lyr.name()))
            if clip_is_2d_bc:
                clip_lyr_mod_si = QgsSpatialIndex(clip_lyr_mod.getFeatures(QgsFeatureRequest(exp)))
            else:
                clip_lyr_mod_si = QgsSpatialIndex(clip_lyr_mod.getFeatures())

        i = 0
        if clip_lyr:
            clip_lyr_mod.startEditing()
        for feat in cn_gen.iter():
            if feedback.isCanceled():
                return {}
            feedback.setCurrentStep(cn_gen.total_steps)
            attr = feat.attributes()
            geom = feat.geometry()

            # split into 2 CN lines
            verts = geom.asPolyline()
            g1 = QgsGeometry.fromPolylineXY(verts[:2])
            g2 = QgsGeometry.fromPolylineXY(verts[1:])
            f1 = QgsFeature()
            f2 = QgsFeature()
            i += 1
            f1.setId(i)
            f1.setGeometry(g1)
            f1.setAttributes(attr)
            i += 1
            f2.setId(i)
            f2.setGeometry(g2)
            f2.setAttributes(attr)

            # insert vertex at intersection with clip layer
            if clip_lyr:
                for fid in clip_lyr_mod_si.intersects(g1.boundingBox()):
                    feat_ = clip_lyr_mod.getFeature(fid)
                    dist, p, iseg, side = feat_.geometry().closestSegmentWithContext(verts[0])
                    if side and not np.isclose(dist, 0., atol=0.001):  # not on segment line
                        continue
                    p, v1, v2, v3, dist = feat_.geometry().closestVertex(verts[0])
                    if dist < 0.1:
                        verts[0] = QgsPointXY(p)
                        g1 = QgsGeometry.fromPolylineXY(verts[:2])
                        f1.setGeometry(g1)
                        break
                    geom = feat_.geometry()
                    geom.insertVertex(verts[0].x(), verts[0].y(), iseg)
                    feat_.setGeometry(geom)
                    clip_lyr_mod.updateFeature(feat_)
                    break
                for fid in clip_lyr_mod_si.intersects(g2.boundingBox()):
                    feat_ = clip_lyr_mod.getFeature(fid)
                    dist, p, iseg, side = feat_.geometry().closestSegmentWithContext(verts[-1])
                    if side and not np.isclose(dist, 0., atol=0.001):  # not on segment line
                        continue
                    p, v1, v2, v3, dist = feat_.geometry().closestVertex(verts[-1])
                    if dist < 0.1:
                        verts[-1] = QgsPointXY(p)
                        g2 = QgsGeometry.fromPolylineXY(verts[1:])
                        f2.setGeometry(g2)
                        break
                    geom = feat_.geometry()
                    geom.insertVertex(verts[-1].x(), verts[-1].y(), iseg)
                    feat_.setGeometry(geom)
                    clip_lyr_mod.updateFeature(feat_)
                    break

            added = sink.addFeature(f1, QgsFeatureSink.FastInsert)
            if not added:
                feedback.reportError('Unable to add features to output')
            added = sink.addFeature(f2, QgsFeatureSink.FastInsert)
            if not added:
                feedback.reportError('Unable to add features to output')

        if clip_lyr:
            clip_lyr_mod.commitChanges()

        feedback.pushInfo(f'\nCN lines created: {cn_gen.total_steps}')

        del sink
        output_layer = QgsProcessingUtils.mapLayerFromString(dest_id, context)
        if output_layer.storageType() == 'Memory storage':
            output_layer.setName('2d_bc_output')

        # set layer - allows renaming if output is memory layer
        context.setLayersToLoadOnCompletion({
            output_layer.id(): QgsProcessingContext.LayerDetails(output_layer.name(), context.project(),
                                                                 output_layer.name()),
        })
        if clip_lyr:
            context.addLayerToLoadOnCompletion(
                clip_lyr_mod.id(), QgsProcessingContext.LayerDetails(clip_lyr_mod.name(), context.project(), clip_lyr_mod.name())
            )
        results['OUTPUT'] = output_layer
        if clip_lyr:
            results['Modified clip layer'] = clip_lyr_mod
        return results

    def name(self):
        return 'Create CN Lines'

    def displayName(self):
        return 'Create CN Lines'

    def shortHelpString(self) -> str:
        folder = Path(os.path.realpath(__file__)).parent
        help_filename = folder / 'help' / 'html' / 'create_cn_lines.html'
        return self.tr(help_filename.open().read().replace('\n', '<p>'))

    def group(self):
        """
        Returns the name of the group this algorithm belongs to.
        """
        return 'miTools'

    def groupId(self):
        return 'miTools'

    def createInstance(self):
        return CreateCNLines()

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)