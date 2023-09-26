import re
from pathlib import Path
from typing import Callable

from PyQt5.QtWidgets import QDialog
from qgis.core import QgsVectorFileWriter, QgsCoordinateTransformContext, QgsProject, QgsVectorLayer
from qgis.utils import plugins

from .plugin import tuflow_plugin
from ..gui import Logging, IncrementLayerDialogBase, IncrementFileDialog, IncrementDbLyrDialog, IncrementLayerDialog
from .map_layer import copy_layer_style


def get_geom_ext(in_name: str) -> str:
    geom_ext = re.findall(r'_[PLR]$', in_name, flags=re.IGNORECASE)
    if geom_ext:
        return geom_ext[0]
    return ''


def get_iter_number(in_name: str, geom_ext: str) -> str:
    iter_number = re.findall(r'\d+(?={0}$)'.format(geom_ext), in_name)
    if iter_number:
        return iter_number[0]


def increment_name(in_name: str) -> str:
    ext = ''
    if Path(in_name).suffix:
        ext = Path(in_name).suffix
        in_name = Path(in_name).stem

    number_part = re.findall(r'_\d+(?:_[PLR])?$', in_name, flags=re.IGNORECASE)
    geom_ext = get_geom_ext(in_name)

    if not number_part:
        if geom_ext:
            out_number_part = f'_001{geom_ext}'
            return re.sub(re.escape(geom_ext), re.escape(out_number_part), in_name) + ext
        else:
            return f'{in_name}_001{ext}'

    out_name = re.sub(re.escape(number_part[0]), '', in_name)
    iter_number = get_iter_number(number_part[0], geom_ext)
    pad = len(iter_number)
    iter_number = f'{int(iter_number) + 1:0{pad}d}'
    return f'{out_name}_{iter_number}{geom_ext}{ext}'


def create_and_load_incremented_layer(
        dlg: IncrementLayerDialogBase,
        on_success: Callable[[QgsVectorLayer, str], None] = None
) -> None:
    iface = tuflow_plugin().iface
    if dlg.result() == QDialog.Accepted:
        for _ in dlg.iter():
            if not dlg.out_file().parent.exists():
                dlg.out_file().parent.mkdir(parents=True, exist_ok=True)
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = dlg.driver_name()
            options.layerName = dlg.output_name
            options.actionOnExistingFile = dlg.action_on_existing
            ret = QgsVectorFileWriter.writeAsVectorFormatV3(dlg.layer,
                                                            str(dlg.out_file()),
                                                            QgsCoordinateTransformContext(),
                                                            options)
            if ret[0] != QgsVectorFileWriter.NoError:
                Logging.error(f'Incrementing error: writing file - {ret[1]}')
                return
            if QgsProject.instance().mapLayer(dlg.layer.id()) and dlg.add_to_canvas:  # old layer is open in workspace
                if dlg.remove_old_layer:  # replace the datasource
                    dlg.layer.setDataSource(dlg.out_data_source(), dlg.output_name, 'ogr')
                else:
                    new_lyr = iface.addVectorLayer(dlg.out_data_source(), dlg.output_name, 'ogr')
                    copy_layer_style(iface, dlg.layer, new_lyr)
            if on_success and hasattr(dlg, 'target_name'):
                on_success(dlg.layer, dlg.target_name)


def increment_file() -> None:
    iface = tuflow_plugin().iface
    dlg = IncrementFileDialog(iface.mainWindow(), iface.activeLayer())
    dlg.accepted.connect(lambda: create_and_load_incremented_layer(dlg))
    dlg.show()


def increment_db_and_lyr() -> None:
    iface = tuflow_plugin().iface
    dlg = IncrementDbLyrDialog(iface.mainWindow(), iface.activeLayer())
    dlg.accepted.connect(lambda: create_and_load_incremented_layer(dlg))
    dlg.show()


def increment_lyr() -> None:
    iface = tuflow_plugin().iface
    dlg = IncrementLayerDialog(iface.mainWindow(), iface.activeLayer())
    dlg.accepted.connect(lambda: create_and_load_incremented_layer(dlg, rename_layer))
    dlg.show()


def rename_layer(layer: QgsVectorLayer, target_name: str) -> None:
    if not target_name:
        return
    file_management = plugins.get('file_management', None)
    if not file_management:
        Logging.error('Unable to rename layer: File Management plugin not found')
        return
    try:
        file_management.rename_layer(layer, target_name)
    except Exception as e:
        Logging.error(f'Unable to rename layer: {e}')
