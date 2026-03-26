from pathlib import Path

from ...pt import pytuflow
from ..logging import Logging

CONTROL_FILE_INPUT_TYPES = [pytuflow.const.INPUT.CF, pytuflow.const.INPUT.DB, pytuflow.const.INPUT.DB_MAT]

from qgis.core import Qgis
BROWSER_LAYER_TYPE = {
    'Point': Qgis.BrowserLayerType.Point,
    'LineString': Qgis.BrowserLayerType.Line,
    'Polygon': Qgis.BrowserLayerType.Polygon
}


def get_pytuflow_class(path: str):
    suffix = Path(path).suffix.lower()
    if suffix == '.tcf':
        return pytuflow.TCF
    elif suffix == '.tgc':
        return pytuflow.TGC
    elif suffix == '.tbc':
        return pytuflow.TBC
    elif suffix == '.ecf':
        return pytuflow.ECF
    elif suffix == '.qcf':
        return pytuflow.QCF
    elif suffix == '.tef':
        return pytuflow.TEF
    elif suffix == '.tesf':
        return pytuflow.TESF
    elif suffix == '.trfcf':
        return pytuflow.TRFCF
    elif suffix == '.adcf':
        return pytuflow.ADCF
    elif suffix == '.tscf':
        return pytuflow.TSCF

from .pd_table_model import PandasTableModel
from .tool_button_delegate import ToolButtonDelegate
from .db_preview_widget import DatabasePreviewWidget

from .browser_helper import init_browser_helper, get_browser_helper

from .run_filter import RunFilters, RunFilterDialog
from .scope_data_item import ScopeDataItem
from .ref_data_item import ReferenceDataItem, ReferenceListDataItem
from .tuflow_data_item_base import TuflowDataItemBaseMixin
from .tuflow_database_item_base import TuflowDatabaseItemMixin
from .tuflow_table_item import TuflowTableItem
from .tuflow_layer_item import TuflowLayerItem

from .control_file_item import ControlFileItem
from .tuflow_browser_provider import TuflowBrowserProvider
