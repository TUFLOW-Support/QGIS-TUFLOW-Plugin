from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox

from forms.ui_replace_features import Ui_dlg_features_from_layer

from qgis.core import QgsMapLayer, QgsWkbTypes, QgsFeatureSink, edit, QgsFeature, QgsFields
from qgis.utils import iface
from toc.toc import tuflowqgis_get_geopackage_from_layer, tuflowqgis_find_layer_in_datasource, tuflowqgis_find_layer, \
    findAllRasterLyrs, findAllVectorLyrsWithGroups


class DlgAddFeaturesFromLayer(QDialog, Ui_dlg_features_from_layer):
    def __init__(self, dest_layer):
        QDialog.__init__(self)
        self.setupUi(self)

        self.dest_layer = dest_layer

        vector_layer_toc_ids = findAllVectorLyrsWithGroups()

        # add vector layers to combobox if appropriate geometry type
        for layer_toc, layer_id in vector_layer_toc_ids:
            layer = tuflowqgis_find_layer(layer_id, search_type='layerid')
            if layer is not None:
                if layer.type() != QgsMapLayer.VectorLayer:
                    continue
                if layer.geometryType() == self.dest_layer.geometryType() and \
                        layer_id != self.dest_layer.id():
                    # source layer can have more fields or up to 2 fewer (ok if no tag/description columns)
                    if layer.fields().count() < self.dest_layer.fields().count() - 2:
                        continue
                    # Make sure the shared fields are compatible
                    for i in range(min(self.dest_layer.fields().count(), layer.fields().count())):
                        dest_qvar = QVariant(self.dest_layer.fields().at(i).type())
                        if not dest_qvar.canConvert(layer.fields().at(i).type()):
                            continue
                    self.comboBox.addItem(layer_toc, layer_id)

        if self.comboBox.count() == 0:
            QMessageBox.warning(self,
                                "No applicable layers found",
                                "Replacing features for a layer requires a source layer with compatible fields. No "
                                "such layers were found")
            self.reject()
            raise ValueError("No applicable layers found")

    def accept(self):
        source_layer_id = self.comboBox.itemData(self.comboBox.currentIndex())
        source_layer = tuflowqgis_find_layer(source_layer_id, search_type='layerid')
        if source_layer is not None:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            self.dest_layer.startEditing()
            self.dest_layer.beginEditCommand('TUFLOW Replace Features')

            # Changed for rollback/save
            # self.dest_layer.dataProvider().truncate()
            features_ids = []
            for curr_feature in self.dest_layer.getFeatures():
                features_ids.append(curr_feature.id())
            self.dest_layer.deleteFeatures(features_ids)

            new_fields_start = self.dest_layer.fields().count()
            for i in range(new_fields_start, source_layer.fields().count()):
                self.dest_layer.addAttribute(source_layer.fields().at(i))

            # Need to do it this way in order for rollback/save option
            # see https://gis.stackexchange.com/questions/320807/cannot-rollback-changes-when-adding-features-to-qgis-layer
            #self.dest_layer.dataProvider().addFeatures(source_layer.dataProvider().getFeatures())
            for feat in source_layer.getFeatures():
                new_feat = QgsFeature()
                new_feat.setGeometry(feat.geometry())
                new_feat.setFields(self.dest_layer.fields())

                # Copy common attributes
                for i_field in range(min(self.dest_layer.fields().count(), source_layer.fields().count())):
                    try:
                        field_name = source_layer.fields().at(i_field).name()
                        new_feat[field_name] = feat[field_name]
                    except:
                        # Names didn't match up don't copy
                        pass

                self.dest_layer.addFeature(new_feat)


            self.dest_layer.endEditCommand()
            # we want to be able to roll-back
            # self.dest_layer.commitChanges(False)

            QApplication.restoreOverrideCursor()

        super().accept()

    def reject(self):
        super().reject()


def run_add_features_from_layer(dest_layer):
    if dest_layer.isEditable():
        QMessageBox.critical(None, "Destination Layer in Edit Sessione",
                             f"The destination layer is in an edit session. Please save or abort changes before "
                             f"continuing.")
        return

    try:
        dlg = DlgAddFeaturesFromLayer(dest_layer)
        dlg.exec()
    except ValueError as e:
        pass


if __name__ == '__main__':
    run_add_features_from_layer()
