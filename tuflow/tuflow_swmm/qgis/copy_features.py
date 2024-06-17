from qgis.core import (QgsFeature,
                       QgsFeatureSink,
                       )


def copy_features(input_layer, output_layer, feedback):
    output_layer.startEditing()
    for feat in input_layer.getFeatures():
        out_feat = QgsFeature()
        out_feat.setGeometry(feat.geometry())
        out_feat.setAttributes(feat.attributes())

        added = output_layer.addFeature(out_feat, QgsFeatureSink.FastInsert)
        if not added:
            feedback.reportError('Unable to add feature to output')
    output_layer.commitChanges()
