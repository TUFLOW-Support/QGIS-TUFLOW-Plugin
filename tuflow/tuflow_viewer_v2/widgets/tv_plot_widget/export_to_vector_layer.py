import typing

from qgis.core import (QgsVectorFileWriter, QgsVectorLayer, QgsField, QgsApplication, QgsProject,
                       QgsVectorFileWriterTask, QgsCoordinateTransform, QgsWkbTypes, Qgis)
from qgis.gui import QgsGui
from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtWidgets import QDialog

from tuflow.compatibility_routines import QT_DIALOG_ACCEPTED


has_save_vector_lyr_dlg = False
if Qgis.QGIS_VERSION_INT >= 33200:
    from qgis.gui import QgsVectorLayerSaveAsDialog
    has_save_vector_lyr_dlg = True


class QgisAppFieldValueConverter(QgsVectorFileWriter.FieldValueConverter):
    """Subclass QgsVectorFileWriter.FieldValueConverter class. Copied from QGIS source code."""

    def __init__(self, layer: QgsVectorLayer, attributes_as_displayed_values: list[int]):
        super().__init__()
        self.layer = layer
        self.attributes_as_displayed_values = attributes_as_displayed_values

    def fieldDefinition(self, field: QgsField) -> QgsField:
        if not self.layer:
            return field
        idx = self.layer.fields().indexFromName(field.name())
        if idx in self.attributes_as_displayed_values:
            return QgsField(field.name(), QMetaType.Type.QString)
        return field

    def convert(self, idx: int, value: QMetaType) -> str:
        if not self.layer:
            return value
        setup = QgsGui.instance().editorWidgetRegistry().findBest(self.layer, self.layer.fields().field(idx).name())
        field_formatter = QgsApplication.instance().fieldFormatterRegistry().fieldFormatter(setup.type())
        return field_formatter.representValue(self.layer, idx, setup.config(), '', value)

    def clone(self) -> QgsVectorFileWriter.FieldValueConverter:
        return QgisAppFieldValueConverter(self.layer, self.attributes_as_displayed_values)


if has_save_vector_lyr_dlg:
    def save_as_vector_file_general(
            layer: QgsVectorLayer,
            symbology_option: bool,
            only_selected: bool,
            default_add_to_map: bool,
            on_success: typing.Callable[[str, bool, str, str, str], None],
            on_failure: typing.Callable[[int, str], None],
            options: QgsVectorLayerSaveAsDialog.Options = QgsVectorLayerSaveAsDialog.Option.AllOptions,
            dialog_name: str = '') -> str:
        """Save layer as vector file. Copied from c++ source from saveAsVectorFileGeneral."""
        from qgis.utils import iface
        dest_crs = QgsProject.instance().crs()
        if not symbology_option:
            options &= ~QgsVectorLayerSaveAsDialog.Option.Symbology
        dialog = QgsVectorLayerSaveAsDialog(layer, QgsVectorLayerSaveAsDialog.Options())
        if dialog_name:
            dialog.setWindowTitle(dialog_name)
        dialog.setMapCanvas(iface.mapCanvas())
        dialog.setIncludeZ(QgsWkbTypes.hasZ(layer.wkbType()))
        dialog.setOnlySelected(only_selected)
        dialog.setAddToCanvas(default_add_to_map)
        if dialog.exec() == QT_DIALOG_ACCEPTED:
            encoding = dialog.encoding()
            layer_name = dialog.layerName()
            vector_file_name = dialog.fileName()
            format = dialog.format()
            datasource_options = dialog.datasourceOptions()
            auto_geometry_type = dialog.automaticGeometryType()
            forced_geometry_type = dialog.geometryType()
            dest_crs = dialog.crs()

            ct = None
            if dest_crs.isValid():
                ct = QgsCoordinateTransform(layer.crs(), dest_crs, QgsProject.instance())

            filter_extent = dialog.filterExtent()
            converter = None
            if not dialog.attributesAsDisplayedValues():
                converter = QgisAppFieldValueConverter(layer, dialog.attributesAsDisplayedValues())
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = format
            options.layerName = layer_name
            options.actionOnExistingFile = dialog.creationActionOnExistingFile()
            options.fileEncoding = encoding
            if ct:
                options.ct = ct
            options.onlySelectedFeatures = dialog.onlySelected()
            options.datasourceOptions = datasource_options
            options.layerOptions = dialog.layerOptions()
            options.skipAttributeCreation = not bool(dialog.selectedAttributes())
            options.symbologyExport = dialog.symbologyExport()
            options.symbologyScale = dialog.scale()
            if dialog.hasFilterExtent():
                options.filterExtent = filter_extent
            options.overrideGeometryType = QgsWkbTypes.Unknown if auto_geometry_type else forced_geometry_type
            options.forceMulti = dialog.forceMulti()
            options.includeZ = dialog.includeZ()
            options.attributes = dialog.selectedAttributes()
            options.attributesExportNames = dialog.attributesExportNames()
            if converter:
                options.fieldValueConverter = converter
            options.saveMetadata = dialog.persistMetadata()
            options.layerMetadata = layer.metadata()

            add_to_canvas = dialog.addToCanvas()
            writer_task = QgsVectorFileWriterTask(layer, vector_file_name, options)
            writer_task.writeComplete.connect(lambda new_file_name: on_success(new_file_name, add_to_canvas, layer_name, encoding, vector_file_name))
            writer_task.errorOccurred.connect(on_failure)
            QgsApplication.instance().taskManager().addTask(writer_task)
            del dialog
            return vector_file_name

        return ''