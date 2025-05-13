from enum import Enum
import shutil

try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from osgeo import ogr
from qgis.PyQt.QtWidgets import QDialog, QFileDialog
from qgis.core import QgsMapLayer, QgsVectorLayer, QgsProject, QgsLayerTreeLayer
from tuflow.forms.SWMM_increment_gpkg import Ui_Increment_gpkg
from tuflow.utils import tuflow_plugin
from tuflow.tuflowqgis_library import tuflowqgis_increment_fname
from tuflow.toc.toc import tuflowqgis_get_all_layers_for_datasource, tuflowqgis_get_geopackage_from_layer


class ExistingOptionsEnum(Enum):
    UNLOAD_ARCHIVE = 0
    UNLOAD = 1
    KEEP_LOADED = 2


class Increment_gpkg(QDialog, Ui_Increment_gpkg):

    def __init__(self, parent: QDialog, gpkg_filename: str) -> None:
        super().__init__()
        self.setupUi(self)

        self.gpkg_filename = gpkg_filename

        self.cbxExistingOptions.addItem('Unload -- move to archive folder')
        self.cbxExistingOptions.addItem('Unload -- do not move')
        self.cbxExistingOptions.addItem('Keep loaded')

        incremented_filename = tuflowqgis_increment_fname(gpkg_filename)
        self.edtOutputFile.setText(incremented_filename)

        self.btnBrowse.clicked.connect(self.browse)

    def browse(self):
        # param = self.gpkg_filename
        # if self.edtOutputFile.text():
        #     start_dir = self.edtOutputFile.text()
        # elif self.project_folder:
        #     start_dir = self.project_folder
        # else:
        #     start_dir = QDir.homePath()
        file = QFileDialog.getSaveFileName(self,
                                           'TUFLOW-SWMM GeoPackage Filename',
                                           self.edtOutputFile.text(),
                                           self.tr('GeoPackages (*.gpkg)'))
        file = file[0]
        if not file:
            return
        self.edtOutputFile.setText(file)

    def unload_orig_layers(self):
        return self.cbxExistingOptions.currentIndex() != ExistingOptionsEnum.KEEP_LOADED.value

    def archive_orig_layers(self):
        archive = self.cbxExistingOptions.currentIndex() == ExistingOptionsEnum.UNLOAD_ARCHIVE.value
        return archive


def run_increment_dlg(gpkg_filename: str, layer: QgsMapLayer) -> None:
    iface = tuflow_plugin().iface
    dlg = Increment_gpkg(iface, gpkg_filename)
    if dlg.exec():
        # User identified an incremented filename. Copy the file and load it into QGIS
        output_filename = dlg.edtOutputFile.text()
        try:
            shutil.copy2(gpkg_filename, output_filename)
        except Exception as e:
            iface.messageBar().pushMessage(f'Error copying file: {str(e)}')
            return

        # Add the layers to the project
        conn = ogr.Open(output_filename)

        # if the initial layer item has a parent, use its parent
        tree_layer = QgsProject.instance().layerTreeRoot().findLayer(layer)
        if tree_layer.parent().parent() is not None:
            insert_before = tree_layer.parent()
        else:
            insert_before = tree_layer

        insert_index = insert_before.parent().children().index(insert_before)

        swmm_group = QgsProject.instance().layerTreeRoot().insertGroup(insert_index,
                                                                       Path(output_filename).stem)

        for i, item in enumerate(conn):
            vlayer = QgsVectorLayer(output_filename + '|layername=' + item.GetName(), item.GetName(), 'ogr')
            if vlayer.isValid():
                QgsProject.instance().addMapLayer(vlayer, False)
            else:
                iface.messageBar().pushMessage(f'Error adding layer: {item.GetName()}')
                return

            swmm_group.insertChildNode(i, QgsLayerTreeLayer(vlayer))

        # Sort the items
        swmm_group.reorderGroupLayers([x.layer() for x in sorted(swmm_group.children(), key=QgsLayerTreeLayer.name)])

        # Unload items if needed
        if dlg.unload_orig_layers():
            layers_to_unload = tuflowqgis_get_all_layers_for_datasource(
                tuflowqgis_get_geopackage_from_layer(layer)
            )
            parent_items = list(set(
                [QgsProject.instance().layerTreeRoot().findLayer(x).parent() for x in layers_to_unload]))
            QgsProject.instance().removeMapLayers([x.id() for x in layers_to_unload])

            # remove blank parent items
            for parent in parent_items:
                if len(parent.children()) == 0:
                    parent.parent().removeChildNode(parent)

            if dlg.archive_orig_layers():
                # get archive folder
                archive_folder = Path(gpkg_filename).parent / 'archive'
                archive_folder.mkdir(parents=True, exist_ok=True)

                # copy the GeoPackage to archive
                shutil.move(gpkg_filename, archive_folder / Path(gpkg_filename).name)
