from qgis.PyQt.QtCore import QSettings, QModelIndex, QItemSelection
from qgis.PyQt.QtWidgets import QDialog, QWidget, QTextBrowser, QVBoxLayout, QBoxLayout
from qgis.PyQt.QtGui import QResizeEvent, QMoveEvent, QStandardItemModel, QStandardItem, QIcon

from .ui_options_dialog import Ui_TuflowViewerOptions
from .general import General
from .formats import Formats
from .debug import Debug
from ...tvinstance import get_viewer_instance


class TVOptionsDialog(QDialog, Ui_TuflowViewerOptions, General, Formats, Debug):

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setupUi(self)
        self.pages = []

        # get the dialog state
        dlg_state = QSettings().value('tuflow_viewer/options_dialog/state', None)
        if dlg_state is not None:
            self.restoreGeometry(dlg_state)

        # get the splitter state
        splitter_state = QSettings().value('tuflow_viewer/options_dialog/splitter_state', None)
        if splitter_state is not None:
            self.splitter.restoreState(splitter_state)
        else:
            self.splitter.setSizes([100, 350])
        self.splitter.splitterMoved.connect(self.splitter_moved)

        self.tree_model = QStandardItemModel(self)
        self.tree_model.appendRow(self.create_item('General', get_viewer_instance().icon('settings.svg', True)))
        self.tree_model.appendRow(self.create_item('Formats', get_viewer_instance().icon('result_formats.svg', True)))
        self.tree_model.appendRow(self.create_item('Debug', get_viewer_instance().icon('debug.svg', True)))

        self.pages.append(self._init_general(self.page_layout))
        self.pages.append(self._init_formats(self.page_layout))
        self.pages.append(self._init_debug(self.page_layout))

        self.options_tree_view.setModel(self.tree_model)
        self.options_tree_view.header().hide()
        idx = QSettings().value('tuflow_viewer/options_dialog/last_index', 0, type=int)
        self.options_tree_view.setCurrentIndex(self.tree_model.index(idx, 0))
        self.current_page = self.get_page_from_index(self.tree_model.index(idx, 0))
        self.current_page.show()

        self.options_tree_view.selectionModel().selectionChanged.connect(lambda x, y: self.index_changed(x, y))

    def create_item(self, name: str, icon: str = ''):
        if icon:
            return QStandardItem(QIcon(icon), name)
        return QStandardItem(name)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        QSettings().setValue('tuflow_viewer/options_dialog/state', self.saveGeometry())

    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        QSettings().setValue('tuflow_viewer/options_dialog/state', self.saveGeometry())

    def splitter_moved(self, pos: int, index: int):
        QSettings().setValue('tuflow_viewer/options_dialog/splitter_state', self.splitter.saveState())

    def get_page_from_index(self, index: QModelIndex) -> QBoxLayout:
        return self.pages[index.row()]

    def index_changed(self, selected: QItemSelection, deselected: QItemSelection):
        self.current_page.hide()
        for index in selected.indexes():
            self.current_page = self.get_page_from_index(index)
            self.current_page.show()
            QSettings().setValue('tuflow_viewer/options_dialog/last_index', index.row())
            break
