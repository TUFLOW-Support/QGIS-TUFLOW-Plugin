from pathlib import Path

from qgis.core import QgsApplication, Qgis, QgsDataItem
from qgis.PyQt import QtGui, QtCore, QtWidgets

from . import (pytuflow, Logging, RunFilters, ReferenceListDataItem, CONTROL_FILE_INPUT_TYPES, RunFilterDialog,
               get_browser_helper)


class TuflowDataItemBaseMixin:

    def _init_tuflow_data_item_base_mixin(self, path: str, inp: pytuflow.Input):
        self._path = path
        self._is_db = False
        self.filter_inherited = False
        self.filter_applied = False
        self._warnings = []
        self.file_exists = pytuflow.TuflowPath(self._path).exists()
        if not self.file_exists:
            self.add_warnings([f'File not found: {Path(self.path()).resolve()}'])
        self.inp = []
        self._inp = None
        if inp is not None:
            self._inp = inp
            self.inp = [inp]

    def _init_filter_state(self):
        self.filter_inherited = False
        self.filter_applied = bool(RunFilters().filter(self._path))
        if self.filter_applied:
            return
        if self.can_have_run_filters() and (isinstance(self._inp, pytuflow.RunState) or self._is_db):
            self.filter_applied = True
            self.filter_inherited = True

    def apply_icon_overlays(self, icon: QtGui.QIcon) -> QtGui.QIcon:
        if self.filter_applied:
            icon = self.add_run_filter_overlay(icon)
        if self._warnings:
            return self.overlay_warning_icon(icon)
        return icon

    def set_tooltip(self):
        tooltip = [self._path]
        run_filter = RunFilters().filter(self._path)
        if run_filter:
            tooltip.append(f'Run Filter: {run_filter}')
        tooltip.extend(self._warnings)
        self.setToolTip('\n'.join(tooltip))

    def add_warnings_from_child(self, child: QgsDataItem):
        if not hasattr(child, '_warnings'):
            return
        for warning in child._warnings:
            if warning not in self._warnings:
                self._warnings.append(warning)
        self.set_tooltip()
        self.dataChanged.emit(self)

    def add_warnings(self, warnings: list[str]):
        self._warnings.extend(warnings)
        self.set_tooltip()
        self.dataChanged.emit(self)

    def add_input(self, inp: pytuflow.Input):
        if not hasattr(self, 'inp'):
            return
        self.inp.append(inp)

    def sort_key(self):
        if self.inp:
            return self.inp[0].line_number
        if hasattr(self, 'name') and self.name():
            return self.name()[0]
        return 0

    def can_have_run_filters(self) -> bool:
        from . import ControlFileItem
        return isinstance(self, ControlFileItem) or self.db

    def tuflow_base_actions(self, parent) -> list[QtWidgets.QAction]:
        actions = []

        if self.inp and self._inp.TUFLOW_TYPE not in CONTROL_FILE_INPUT_TYPES:
            return actions

        if self.providerKey() == 'tuflow_plugin':
            action_open_in_editor = QtGui.QAction('Open in External Editor', parent)
            action_open_in_editor.triggered.connect(
                lambda x: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(self.path())))
            actions.append(action_open_in_editor)
            if self.inp is not None:
                action_open_file_loc = QtGui.QAction('Open File Location', parent)
                action_open_file_loc.triggered.connect(
                    lambda x: QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(Path(self._path).parent))))
                actions.append(action_open_file_loc)
            sep = QtWidgets.QAction(parent)
            sep.setSeparator(True)
            actions.append(sep)

        text = 'Edit Run Filter' if RunFilters().filter(self._path) else 'Add Run Filter'
        if self.filter_inherited and text == 'Edit Run Filter':
            pass
        else:
            action_add_run_filter = QtGui.QAction(text, parent)
            action_add_run_filter.triggered.connect(self.add_run_filter)
            actions.append(action_add_run_filter)
        if RunFilters().filter(self.path()) and not self.filter_inherited:
            action_rem_filter = QtGui.QAction('Clear Run Filter', parent)
            action_rem_filter.triggered.connect(self.clear_run_filter)
            actions.append(action_rem_filter)

        return actions

    def add_run_filter(self, checked: bool = True, run_filter: str = None):
        gui_thread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not gui_thread:
            Logging.warning('Cannot create run filter input widget on non-GUI thread')
            return

        menu = self.sender().parent()
        dlg = RunFilterDialog(parent=menu, current_filter=RunFilters().filter(self._path))

        if dlg.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return
        run_filter = dlg.filter_input.text()

        RunFilters().add_filter(self._path, run_filter)
        self.filter_applied = True
        self.dataChanged.emit(self)

        browser_helper = get_browser_helper()
        if not browser_helper:
            Logging.warning('Browser helper not initialized, cannot propagate run filter to children')
            return

        self.set_tooltip()
        self.refresh()
        browser_helper.filter_changed(self)

    def clear_run_filter(self, checked: bool = True):
        gui_thread = QtCore.QThread.currentThread() == QtCore.QCoreApplication.instance().thread()
        if not gui_thread:
            Logging.warning('Cannot clear run filter from non-GUI thread')
            return

        RunFilters().clear_filter(self._path)
        self.filter_applied = False

        browser_helper = get_browser_helper()
        if not browser_helper:
            Logging.warning('Browser helper not initialized, cannot propagate clear run filter to children')
            return

        self.set_tooltip()
        self.refresh()
        browser_helper.filter_changed(self)

    def overlay_warning_icon(self, icon: QtGui.QIcon) -> QtGui.QIcon:
        try:
            warning_icon = QgsApplication.getThemeIcon('/mIconWarning.svg')

            # draw warning icon as an overlay
            size = 16
            base_pixmap = icon.pixmap(size, size)
            overlay_pixmap = warning_icon.pixmap(size // 2, size // 2)

            result = QtGui.QPixmap(size, size)
            result.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QtGui.QPainter(result)
            painter.drawPixmap(0, 0, base_pixmap)

            x = size - overlay_pixmap.width()
            y = size - overlay_pixmap.height()

            painter.drawPixmap(x, y, overlay_pixmap)

            # add a red squiggly underline
            pen = QtGui.QPen(QtCore.Qt.GlobalColor.red)
            pen.setWidthF(2.)
            painter.setPen(pen)

            amplitude = 1
            wavelength = 2.5
            y_base = size - amplitude - 1

            path = QtGui.QPainterPath()
            x = 0
            path.moveTo(0, y_base)

            toggle = True
            while x <= size:
                y = y_base - amplitude if toggle else y_base + amplitude
                path.lineTo(x, y)
                toggle = not toggle
                x += wavelength

            # painter.drawRect(0, 0, base_pixmap.width(), base_pixmap.height())
            painter.drawPath(path)
            painter.end()

            return QtGui.QIcon(result)
        except Exception as e:
            Logging.warning(f'Failed to overlay warning icon: {e}', silent=True)
        return icon

    def add_run_filter_overlay(self, icon: QtGui.QIcon) -> QtGui.QIcon:
        try:
            path = Path(__file__).parents[2] / 'icons' / 'run.svg'
            run_icon = QtGui.QIcon(str(path))
            size = 16
            base_size = int(size * 2 // 3)
            overlay_size = int(size * 3 // 4)
            base_pixmap = icon.pixmap(base_size, base_size)
            overlay_pixmap = run_icon.pixmap(overlay_size, overlay_size)

            result = QtGui.QPixmap(size, size)
            result.fill(QtCore.Qt.GlobalColor.transparent)

            painter = QtGui.QPainter(result)
            painter.drawPixmap(1, 1, base_pixmap)

            x = size - overlay_size
            y = size - overlay_size

            painter.drawPixmap(x, y, overlay_pixmap)

            # add a green outline
            pen = QtGui.QPen(QtGui.QColor('#53d46d'))
            pen.setWidthF(2.)
            painter.setPen(pen)
            painter.drawRect(0, 0, size, size)

            painter.end()
            return QtGui.QIcon(result)
        except Exception:
            pass
        return icon

    @staticmethod
    def _create_children(parent: QgsDataItem) -> list[QgsDataItem]:
        children = []
        if not hasattr(parent, 'inp') or not parent.inp:
            return children

        # children.append(scope_item)
        ref_item = ReferenceListDataItem(
            QgsDataItem.Custom,
            parent,
            '_References',
            parent.path() + '/References/', 'tuflow_plugin',
            {inp: f'Line {inp.line_number}: {inp}' for inp in parent.inp}
        )
        children.append(ref_item)
        return children