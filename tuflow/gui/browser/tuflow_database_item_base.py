from pathlib import Path

from qgis.PyQt import QtCore, QtWidgets, QtGui

from . import pytuflow, Logging, RunFilters, TuflowDataItemBaseMixin, DatabasePreviewWidget


class TuflowDatabaseItemMixin:

    def _init_tuflow_database_mixin(self, inp: pytuflow.Input):
        self.db = None
        self._is_db = inp.TUFLOW_TYPE in [pytuflow.const.INPUT.DB, pytuflow.const.INPUT.DB_MAT]
        if not self._is_db:
            if inp.TUFLOW_TYPE == pytuflow.const.INPUT.GIS and inp.cf:
                self._is_db = True
        self._preview_widget = None

    def _init_database(self: TuflowDataItemBaseMixin, inp: pytuflow.Input):
        dbs = [x for x in inp.cf if x.fpath.resolve() == Path(self._path).resolve()]
        if dbs:
            self.db = dbs[0]
        else:
            Logging.warning(f'Could not find database for path: {self._path}')
        if isinstance(self.db, pytuflow.RunState):
            self.filter_applied = True
            self.filter_inherited = True
        elif RunFilters().filter(self._path):
            run_filter = RunFilters().filter(self._path)
            self._filter_applied = True
            try:
                if self.db:
                    self.db = self.db.context(run_filter)
            except Exception as e:
                Logging.warning(f'Failed to apply run filter to control file in QGIS Browser: {e}', silent=True)
                self.add_warnings([f'Failed to apply run filter: {run_filter}: {e}'])

    def database_actions(self, parent) -> list[QtWidgets.QAction]:
        actions = []
        if not self._is_db:
            return actions
        if not self.db.fpath.exists():
            return actions
        action_preview = QtGui.QAction('Preview Data', parent)
        action_preview.triggered.connect(self.preview_data)
        actions.append(action_preview)
        return actions

    def preview_data(self):
        gui_thread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not gui_thread:
            Logging.warning('Cannot create preview widget on non-GUI thread')
            return

        menu = self.sender().parent()
        self._preview_widget = DatabasePreviewWidget(menu, self.db)
        self._preview_widget.closed.connect(self._preview_widget.deleteLater)
        self._preview_widget.show()