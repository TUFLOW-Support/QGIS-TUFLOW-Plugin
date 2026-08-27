from pathlib import Path

from qgis.PyQt import QtGui, QtCore, QtWidgets

from . import pytuflow, DatabasePreviewWidget, Logging, get_pytuflow_class, SUPPORTED_EXTS


class FVDataItemMixin:

    def _init_fv_mixin(self, path: str):
        self._path = path
        self._cf = None

    def fv_actions(self, parent, cf: pytuflow.FVBaseMixin | None) -> list[QtWidgets.QAction]:
        self._cf = cf if self.cf is not None else get_pytuflow_class(self._path)(self._path)
        if self._cf.root_cf != self._cf or Path(self.parent().path()).suffix.lower() in SUPPORTED_EXTS:
            return []

        actions = []

        if Path(self._path).suffix.lower() == '.fvc':
            bc_dbase_action = QtWidgets.QAction('Preview bc_dbase...', parent)
            bc_dbase_action.triggered.connect(lambda b, db_type='bc_dbase': self.preview_data(db_type))
            actions.append(bc_dbase_action)

            mat_dbase_action = QtWidgets.QAction('Preview mat file...', parent)
            mat_dbase_action.triggered.connect(lambda b, db_type='mat_file': self.preview_data(db_type))
            actions.append(mat_dbase_action)

        return actions

    def preview_data(self, db_type: str):
        gui_thread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not gui_thread:
            Logging.warning('Cannot create preview widget on non-GUI thread', silent=True)
            return

        if self._cf is None:
            Logging.warning('Control file is not set, cannot preview data', silent=True)
            return

        if db_type == 'bc_dbase':
            db = self._cf.bc_dbase()
        elif db_type == 'mat_file':
            db = self._cf.mat_file()
        else:
            Logging.warning(f'Unknown database type: {db_type}', silent=True)
            return

        menu = self.sender().parent()
        self._preview_widget = DatabasePreviewWidget(menu, db)
        self._preview_widget.closed.connect(self._preview_widget.deleteLater)
        self._preview_widget.show()
